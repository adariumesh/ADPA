"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const react_1 = __importDefault(require("react"));
const react_router_dom_1 = require("react-router-dom");
const material_1 = require("@mui/material");
const theme_1 = require("./theme");
const Layout_1 = __importDefault(require("./components/Layout"));
const Dashboard_1 = __importDefault(require("./components/Dashboard"));
const PipelineBuilder_1 = __importDefault(require("./components/PipelineBuilder"));
const PipelineMonitor_1 = __importDefault(require("./components/PipelineMonitor"));
const ResultsViewer_1 = __importDefault(require("./components/ResultsViewer"));
function App() {
    return (<material_1.ThemeProvider theme={theme_1.theme}>
      <material_1.CssBaseline />
      <react_router_dom_1.BrowserRouter>
        <Layout_1.default>
          <react_router_dom_1.Routes>
            <react_router_dom_1.Route path="/" element={<Dashboard_1.default />}/>
            <react_router_dom_1.Route path="/builder" element={<PipelineBuilder_1.default />}/>
            <react_router_dom_1.Route path="/monitor" element={<PipelineMonitor_1.default />}/>
            <react_router_dom_1.Route path="/results" element={<ResultsViewer_1.default />}/>
          </react_router_dom_1.Routes>
        </Layout_1.default>
      </react_router_dom_1.BrowserRouter>
    </material_1.ThemeProvider>);
}
exports.default = App;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiQXBwLmpzIiwic291cmNlUm9vdCI6IiIsInNvdXJjZXMiOlsiQXBwLnRzeCJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiOzs7OztBQUFBLGtEQUEwQjtBQUMxQix1REFBMEU7QUFDMUUsNENBQTJEO0FBQzNELG1DQUFnQztBQUNoQyxpRUFBeUM7QUFDekMsdUVBQStDO0FBQy9DLG1GQUEyRDtBQUMzRCxtRkFBMkQ7QUFDM0QsK0VBQXVEO0FBRXZELFNBQVMsR0FBRztJQUNWLE9BQU8sQ0FDTCxDQUFDLHdCQUFhLENBQUMsS0FBSyxDQUFDLENBQUMsYUFBSyxDQUFDLENBQzFCO01BQUEsQ0FBQyxzQkFBVyxDQUFDLEFBQUQsRUFDWjtNQUFBLENBQUMsZ0NBQU0sQ0FDTDtRQUFBLENBQUMsZ0JBQU0sQ0FDTDtVQUFBLENBQUMseUJBQU0sQ0FDTDtZQUFBLENBQUMsd0JBQUssQ0FBQyxJQUFJLENBQUMsR0FBRyxDQUFDLE9BQU8sQ0FBQyxDQUFDLENBQUMsbUJBQVMsQ0FBQyxBQUFELEVBQUcsQ0FBQyxFQUN2QztZQUFBLENBQUMsd0JBQUssQ0FBQyxJQUFJLENBQUMsVUFBVSxDQUFDLE9BQU8sQ0FBQyxDQUFDLENBQUMseUJBQWUsQ0FBQyxBQUFELEVBQUcsQ0FBQyxFQUNwRDtZQUFBLENBQUMsd0JBQUssQ0FBQyxJQUFJLENBQUMsVUFBVSxDQUFDLE9BQU8sQ0FBQyxDQUFDLENBQUMseUJBQWUsQ0FBQyxBQUFELEVBQUcsQ0FBQyxFQUNwRDtZQUFBLENBQUMsd0JBQUssQ0FBQyxJQUFJLENBQUMsVUFBVSxDQUFDLE9BQU8sQ0FBQyxDQUFDLENBQUMsdUJBQWEsQ0FBQyxBQUFELEVBQUcsQ0FBQyxFQUNwRDtVQUFBLEVBQUUseUJBQU0sQ0FDVjtRQUFBLEVBQUUsZ0JBQU0sQ0FDVjtNQUFBLEVBQUUsZ0NBQU0sQ0FDVjtJQUFBLEVBQUUsd0JBQWEsQ0FBQyxDQUNqQixDQUFDO0FBQ0osQ0FBQztBQUVELGtCQUFlLEdBQUcsQ0FBQyIsInNvdXJjZXNDb250ZW50IjpbImltcG9ydCBSZWFjdCBmcm9tICdyZWFjdCc7XG5pbXBvcnQgeyBCcm93c2VyUm91dGVyIGFzIFJvdXRlciwgUm91dGVzLCBSb3V0ZSB9IGZyb20gJ3JlYWN0LXJvdXRlci1kb20nO1xuaW1wb3J0IHsgVGhlbWVQcm92aWRlciwgQ3NzQmFzZWxpbmUgfSBmcm9tICdAbXVpL21hdGVyaWFsJztcbmltcG9ydCB7IHRoZW1lIH0gZnJvbSAnLi90aGVtZSc7XG5pbXBvcnQgTGF5b3V0IGZyb20gJy4vY29tcG9uZW50cy9MYXlvdXQnO1xuaW1wb3J0IERhc2hib2FyZCBmcm9tICcuL2NvbXBvbmVudHMvRGFzaGJvYXJkJztcbmltcG9ydCBQaXBlbGluZUJ1aWxkZXIgZnJvbSAnLi9jb21wb25lbnRzL1BpcGVsaW5lQnVpbGRlcic7XG5pbXBvcnQgUGlwZWxpbmVNb25pdG9yIGZyb20gJy4vY29tcG9uZW50cy9QaXBlbGluZU1vbml0b3InO1xuaW1wb3J0IFJlc3VsdHNWaWV3ZXIgZnJvbSAnLi9jb21wb25lbnRzL1Jlc3VsdHNWaWV3ZXInO1xuXG5mdW5jdGlvbiBBcHAoKSB7XG4gIHJldHVybiAoXG4gICAgPFRoZW1lUHJvdmlkZXIgdGhlbWU9e3RoZW1lfT5cbiAgICAgIDxDc3NCYXNlbGluZSAvPlxuICAgICAgPFJvdXRlcj5cbiAgICAgICAgPExheW91dD5cbiAgICAgICAgICA8Um91dGVzPlxuICAgICAgICAgICAgPFJvdXRlIHBhdGg9XCIvXCIgZWxlbWVudD17PERhc2hib2FyZCAvPn0gLz5cbiAgICAgICAgICAgIDxSb3V0ZSBwYXRoPVwiL2J1aWxkZXJcIiBlbGVtZW50PXs8UGlwZWxpbmVCdWlsZGVyIC8+fSAvPlxuICAgICAgICAgICAgPFJvdXRlIHBhdGg9XCIvbW9uaXRvclwiIGVsZW1lbnQ9ezxQaXBlbGluZU1vbml0b3IgLz59IC8+XG4gICAgICAgICAgICA8Um91dGUgcGF0aD1cIi9yZXN1bHRzXCIgZWxlbWVudD17PFJlc3VsdHNWaWV3ZXIgLz59IC8+XG4gICAgICAgICAgPC9Sb3V0ZXM+XG4gICAgICAgIDwvTGF5b3V0PlxuICAgICAgPC9Sb3V0ZXI+XG4gICAgPC9UaGVtZVByb3ZpZGVyPlxuICApO1xufVxuXG5leHBvcnQgZGVmYXVsdCBBcHA7XG4iXX0=