import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql.functions import col, sum as _sum, count as _count

args = getResolvedOptions(sys.argv, ['JOB_NAME','CURATED_BUCKET'])
cur = args['CURATED_BUCKET']

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

sales = spark.read.parquet(f's3://{cur}/adpa/curated/sales_clean/')
users = spark.read.parquet(f's3://{cur}/adpa/curated/users_clean/')

feat = sales.groupBy('customer_id').agg(
    _sum('revenue').alias('total_revenue'),
    _count('*').alias('order_count')
).withColumnRenamed('customer_id','user_id')

features = users.join(feat, on='user_id', how='left').fillna({'total_revenue':0.0,'order_count':0})
features.write.mode('overwrite').parquet(f's3://{cur}/adpa/curated/features_user_sales/')

job.commit()