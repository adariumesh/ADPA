"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.theme = void 0;
const styles_1 = require("@mui/material/styles");
exports.theme = (0, styles_1.createTheme)({
    palette: {
        primary: {
            main: '#1976d2',
            light: '#42a5f5',
            dark: '#1565c0',
        },
        secondary: {
            main: '#dc004e',
            light: '#ff5983',
            dark: '#9a0036',
        },
        background: {
            default: '#f5f5f5',
            paper: '#ffffff',
        },
        success: {
            main: '#4caf50',
        },
        warning: {
            main: '#ff9800',
        },
        error: {
            main: '#f44336',
        },
    },
    typography: {
        fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
        h4: {
            fontWeight: 600,
        },
        h5: {
            fontWeight: 500,
        },
        h6: {
            fontWeight: 500,
        },
    },
    components: {
        MuiCard: {
            styleOverrides: {
                root: {
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                    borderRadius: 8,
                },
            },
        },
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 6,
                    textTransform: 'none',
                },
            },
        },
        MuiChip: {
            styleOverrides: {
                root: {
                    borderRadius: 16,
                },
            },
        },
    },
});
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoidGhlbWUuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyJ0aGVtZS50cyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiOzs7QUFBQSxpREFBbUQ7QUFFdEMsUUFBQSxLQUFLLEdBQUcsSUFBQSxvQkFBVyxFQUFDO0lBQy9CLE9BQU8sRUFBRTtRQUNQLE9BQU8sRUFBRTtZQUNQLElBQUksRUFBRSxTQUFTO1lBQ2YsS0FBSyxFQUFFLFNBQVM7WUFDaEIsSUFBSSxFQUFFLFNBQVM7U0FDaEI7UUFDRCxTQUFTLEVBQUU7WUFDVCxJQUFJLEVBQUUsU0FBUztZQUNmLEtBQUssRUFBRSxTQUFTO1lBQ2hCLElBQUksRUFBRSxTQUFTO1NBQ2hCO1FBQ0QsVUFBVSxFQUFFO1lBQ1YsT0FBTyxFQUFFLFNBQVM7WUFDbEIsS0FBSyxFQUFFLFNBQVM7U0FDakI7UUFDRCxPQUFPLEVBQUU7WUFDUCxJQUFJLEVBQUUsU0FBUztTQUNoQjtRQUNELE9BQU8sRUFBRTtZQUNQLElBQUksRUFBRSxTQUFTO1NBQ2hCO1FBQ0QsS0FBSyxFQUFFO1lBQ0wsSUFBSSxFQUFFLFNBQVM7U0FDaEI7S0FDRjtJQUNELFVBQVUsRUFBRTtRQUNWLFVBQVUsRUFBRSw0Q0FBNEM7UUFDeEQsRUFBRSxFQUFFO1lBQ0YsVUFBVSxFQUFFLEdBQUc7U0FDaEI7UUFDRCxFQUFFLEVBQUU7WUFDRixVQUFVLEVBQUUsR0FBRztTQUNoQjtRQUNELEVBQUUsRUFBRTtZQUNGLFVBQVUsRUFBRSxHQUFHO1NBQ2hCO0tBQ0Y7SUFDRCxVQUFVLEVBQUU7UUFDVixPQUFPLEVBQUU7WUFDUCxjQUFjLEVBQUU7Z0JBQ2QsSUFBSSxFQUFFO29CQUNKLFNBQVMsRUFBRSwyQkFBMkI7b0JBQ3RDLFlBQVksRUFBRSxDQUFDO2lCQUNoQjthQUNGO1NBQ0Y7UUFDRCxTQUFTLEVBQUU7WUFDVCxjQUFjLEVBQUU7Z0JBQ2QsSUFBSSxFQUFFO29CQUNKLFlBQVksRUFBRSxDQUFDO29CQUNmLGFBQWEsRUFBRSxNQUFNO2lCQUN0QjthQUNGO1NBQ0Y7UUFDRCxPQUFPLEVBQUU7WUFDUCxjQUFjLEVBQUU7Z0JBQ2QsSUFBSSxFQUFFO29CQUNKLFlBQVksRUFBRSxFQUFFO2lCQUNqQjthQUNGO1NBQ0Y7S0FDRjtDQUNGLENBQUMsQ0FBQyIsInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IGNyZWF0ZVRoZW1lIH0gZnJvbSAnQG11aS9tYXRlcmlhbC9zdHlsZXMnO1xuXG5leHBvcnQgY29uc3QgdGhlbWUgPSBjcmVhdGVUaGVtZSh7XG4gIHBhbGV0dGU6IHtcbiAgICBwcmltYXJ5OiB7XG4gICAgICBtYWluOiAnIzE5NzZkMicsXG4gICAgICBsaWdodDogJyM0MmE1ZjUnLFxuICAgICAgZGFyazogJyMxNTY1YzAnLFxuICAgIH0sXG4gICAgc2Vjb25kYXJ5OiB7XG4gICAgICBtYWluOiAnI2RjMDA0ZScsXG4gICAgICBsaWdodDogJyNmZjU5ODMnLFxuICAgICAgZGFyazogJyM5YTAwMzYnLFxuICAgIH0sXG4gICAgYmFja2dyb3VuZDoge1xuICAgICAgZGVmYXVsdDogJyNmNWY1ZjUnLFxuICAgICAgcGFwZXI6ICcjZmZmZmZmJyxcbiAgICB9LFxuICAgIHN1Y2Nlc3M6IHtcbiAgICAgIG1haW46ICcjNGNhZjUwJyxcbiAgICB9LFxuICAgIHdhcm5pbmc6IHtcbiAgICAgIG1haW46ICcjZmY5ODAwJyxcbiAgICB9LFxuICAgIGVycm9yOiB7XG4gICAgICBtYWluOiAnI2Y0NDMzNicsXG4gICAgfSxcbiAgfSxcbiAgdHlwb2dyYXBoeToge1xuICAgIGZvbnRGYW1pbHk6ICdcIlJvYm90b1wiLCBcIkhlbHZldGljYVwiLCBcIkFyaWFsXCIsIHNhbnMtc2VyaWYnLFxuICAgIGg0OiB7XG4gICAgICBmb250V2VpZ2h0OiA2MDAsXG4gICAgfSxcbiAgICBoNToge1xuICAgICAgZm9udFdlaWdodDogNTAwLFxuICAgIH0sXG4gICAgaDY6IHtcbiAgICAgIGZvbnRXZWlnaHQ6IDUwMCxcbiAgICB9LFxuICB9LFxuICBjb21wb25lbnRzOiB7XG4gICAgTXVpQ2FyZDoge1xuICAgICAgc3R5bGVPdmVycmlkZXM6IHtcbiAgICAgICAgcm9vdDoge1xuICAgICAgICAgIGJveFNoYWRvdzogJzAgMnB4IDRweCByZ2JhKDAsMCwwLDAuMSknLFxuICAgICAgICAgIGJvcmRlclJhZGl1czogOCxcbiAgICAgICAgfSxcbiAgICAgIH0sXG4gICAgfSxcbiAgICBNdWlCdXR0b246IHtcbiAgICAgIHN0eWxlT3ZlcnJpZGVzOiB7XG4gICAgICAgIHJvb3Q6IHtcbiAgICAgICAgICBib3JkZXJSYWRpdXM6IDYsXG4gICAgICAgICAgdGV4dFRyYW5zZm9ybTogJ25vbmUnLFxuICAgICAgICB9LFxuICAgICAgfSxcbiAgICB9LFxuICAgIE11aUNoaXA6IHtcbiAgICAgIHN0eWxlT3ZlcnJpZGVzOiB7XG4gICAgICAgIHJvb3Q6IHtcbiAgICAgICAgICBib3JkZXJSYWRpdXM6IDE2LFxuICAgICAgICB9LFxuICAgICAgfSxcbiAgICB9LFxuICB9LFxufSk7Il19