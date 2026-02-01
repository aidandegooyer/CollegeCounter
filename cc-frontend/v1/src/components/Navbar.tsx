import { Input } from "./ui/input";
import { NavLink, useLocation } from "react-router";
import logo from "../assets/0.1x/C Logo@0.1x.png";

function Navbar() {
  const location = useLocation();

  const isDevelopment =
    import.meta.env.VITE_API_BASE_URL?.includes("localhost") ||
    import.meta.env.VITE_API_BASE_URL?.includes("127.0.0.1");

  return (
    <nav className="bg-background/80 border-border sticky top-0 z-50 w-full px-4 py-3 backdrop-blur-md">
      {isDevelopment && (
        <div className="mb-4 bg-yellow-500 px-4 py-2 text-center text-sm font-semibold text-black">
          🚧 DEVELOPMENT MODE - Using local API
        </div>
      )}
      <div className="container mx-auto flex max-w-[1200px] items-center justify-between">
        <NavLink to="/" className="flex items-center">
          <img
            src={logo}
            alt="College Counter Logo"
            className="mr-2 h-10 w-10 rounded-sm"
          />
          <div
            className={`font-block hidden text-3xl lg:block ${
              location.pathname === "/"
                ? "text-foreground"
                : "text-muted-foreground"
            }`}
          >
            College Counter
          </div>
        </NavLink>
        <ul className="flex space-x-6">
          <li>
            <NavLink
              to="/news"
              className={`transition-colors hover:text-blue-200 ${
                location.pathname === "/news"
                  ? "text-foreground"
                  : "text-muted-foreground"
              }`}
            >
              News
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/rankings"
              className={`transition-colors hover:text-blue-200 ${
                location.pathname === "/rankings"
                  ? "text-foreground"
                  : "text-muted-foreground"
              }`}
            >
              Rankings
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/matches"
              className={`transition-colors hover:text-blue-200 ${
                location.pathname === "/matches"
                  ? "text-foreground"
                  : "text-muted-foreground"
              }`}
            >
              Matches
            </NavLink>
          </li>

          <li>
            <NavLink
              to={"/events"}
              className={`transition-colors hover:text-blue-200 ${
                location.pathname === "/events"
                  ? "text-foreground"
                  : "text-muted-foreground"
              }`}
            >
              Events
            </NavLink>
          </li>
        </ul>
        <div className="hidden md:block">
          <SearchInput />
        </div>
      </div>
      <div className="mt-2 block md:hidden">
        <SearchInput />
      </div>
    </nav>
  );
}

export default Navbar;

function SearchInput() {
  return (
    <div>
      <Input placeholder="Search (coming soon)" autoComplete="off" disabled />
    </div>
  );
}
