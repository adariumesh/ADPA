import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext

args = getResolvedOptions(sys.argv, ['JOB_NAME','RAW_BUCKET','CURATED_BUCKET'])
raw = args['RAW_BUCKET']
cur = args['CURATED_BUCKET']

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Sales (CSV)
sales = spark.read.option('header','true').csv(f's3://{raw}/adpa/raw/sales/sales.csv')
sales = sales.withColumn('quantity', sales.quantity.cast('int')) \
             .withColumn('unit_price', sales.unit_price.cast('double'))
from pyspark.sql.functions import col, when, expr
sales = sales.where((col('quantity') > 0) & (col('unit_price') > 0)) \
             .withColumn('revenue', expr('quantity * unit_price'))
sales.write.mode('overwrite').parquet(f's3://{cur}/adpa/curated/sales_clean/')

# Users (JSONL)
users = spark.read.json(f's3://{raw}/adpa/raw/users/users.jsonl')
from pyspark.sql.functions import lower
users = users.dropna(subset=['user_id','email']).withColumn('email', lower(col('email')))
users.createOrReplaceTempView('users')
users_clean = spark.sql('''
  SELECT user_id, email, country, max(signup_ts) as signup_ts
  FROM users
  GROUP BY user_id, email, country
''')
users_clean.write.mode('overwrite').parquet(f's3://{cur}/adpa/curated/users_clean/')

# Events (Parquet)
events = spark.read.parquet(f's3://{raw}/adpa/raw/events/events.parquet')
from pyspark.sql.functions import when
events = events.withColumn('event_type', when(col('event_type').isin('view','click','add_to_cart','purchase'), col('event_type')).otherwise('other')) \
               .dropna(subset=['user_id'])
events.write.mode('overwrite').parquet(f's3://{cur}/adpa/curated/events_clean/')

job.commit()