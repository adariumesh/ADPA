"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const react_1 = __importDefault(require("react"));
const react_2 = require("@testing-library/react");
const App_1 = __importDefault(require("./App"));
test('renders learn react link', () => {
    (0, react_2.render)(<App_1.default />);
    const linkElement = react_2.screen.getByText(/learn react/i);
    expect(linkElement).toBeInTheDocument();
});
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiQXBwLnRlc3QuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyJBcHAudGVzdC50c3giXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7QUFBQSxrREFBMEI7QUFDMUIsa0RBQXdEO0FBQ3hELGdEQUF3QjtBQUV4QixJQUFJLENBQUMsMEJBQTBCLEVBQUUsR0FBRyxFQUFFO0lBQ3BDLElBQUEsY0FBTSxFQUFDLENBQUMsYUFBRyxDQUFDLEFBQUQsRUFBRyxDQUFDLENBQUM7SUFDaEIsTUFBTSxXQUFXLEdBQUcsY0FBTSxDQUFDLFNBQVMsQ0FBQyxjQUFjLENBQUMsQ0FBQztJQUNyRCxNQUFNLENBQUMsV0FBVyxDQUFDLENBQUMsaUJBQWlCLEVBQUUsQ0FBQztBQUMxQyxDQUFDLENBQUMsQ0FBQyIsInNvdXJjZXNDb250ZW50IjpbImltcG9ydCBSZWFjdCBmcm9tICdyZWFjdCc7XG5pbXBvcnQgeyByZW5kZXIsIHNjcmVlbiB9IGZyb20gJ0B0ZXN0aW5nLWxpYnJhcnkvcmVhY3QnO1xuaW1wb3J0IEFwcCBmcm9tICcuL0FwcCc7XG5cbnRlc3QoJ3JlbmRlcnMgbGVhcm4gcmVhY3QgbGluaycsICgpID0+IHtcbiAgcmVuZGVyKDxBcHAgLz4pO1xuICBjb25zdCBsaW5rRWxlbWVudCA9IHNjcmVlbi5nZXRCeVRleHQoL2xlYXJuIHJlYWN0L2kpO1xuICBleHBlY3QobGlua0VsZW1lbnQpLnRvQmVJblRoZURvY3VtZW50KCk7XG59KTtcbiJdfQ==