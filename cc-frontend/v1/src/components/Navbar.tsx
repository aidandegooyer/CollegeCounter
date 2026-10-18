import { Input } from "./ui/input";
import { Button } from "./ui/button";
import {
  NavLink,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router";
import { useEffect, useState } from "react";
import logo from "../assets/0.1x/C Logo@0.1x.png";
import { ChevronDown, Menu, Search, X } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";

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
        <ul className="flex items-center space-x-6">
          {PRIMARY_LINKS.map((link) => (
            <li key={link.to} className="hidden sm:block">
              <NavLink
                to={link.to}
                className={`transition-colors hover:text-blue-200 ${
                  location.pathname === link.to
                    ? "text-foreground"
                    : "text-muted-foreground"
                }`}
              >
                {link.label}
              </NavLink>
            </li>
          ))}
          <li>
            <MoreMenu />
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

const PRIMARY_LINKS = [
  { to: "/news", label: "News" },
  { to: "/rankings", label: "Rankings" },
  { to: "/matches", label: "Matches" },
];

const MORE_LINKS = [
  { to: "/events", label: "Events" },
  { to: "/head-to-head", label: "Head to Head" },
  { to: "/about", label: "About Us" },
];

// Less-used pages, grouped to keep the navbar from crowding. On mobile the
// primary links collapse into this menu too.
function MoreMenu() {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);

  const isActive = (to: string) =>
    location.pathname === to || location.pathname.startsWith(`${to}/`);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger
        className={`flex cursor-pointer items-center gap-1 transition-colors hover:text-blue-200 ${
          MORE_LINKS.some((link) => isActive(link.to))
            ? "text-foreground"
            : "text-muted-foreground"
        }`}
      >
        {isOpen ? (
          <X className="size-6 sm:hidden" />
        ) : (
          <Menu className="size-6 sm:hidden" />
        )}
        <span className="sr-only sm:hidden">Menu</span>
        <span className="hidden items-center gap-1 sm:flex">
          More
          <ChevronDown
            className={`size-4 transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        </span>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-48 p-1 sm:w-40">
        <ul>
          {PRIMARY_LINKS.map((link) => (
            <li key={link.to} className="sm:hidden">
              <NavLink
                to={link.to}
                onClick={() => setIsOpen(false)}
                className={`hover:bg-muted block rounded-sm px-2 py-2 transition-colors ${
                  isActive(link.to)
                    ? "text-foreground"
                    : "text-muted-foreground"
                }`}
              >
                {link.label}
              </NavLink>
            </li>
          ))}
          {MORE_LINKS.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                onClick={() => setIsOpen(false)}
                className={`hover:bg-muted block rounded-sm px-2 py-2 transition-colors sm:py-1.5 sm:text-sm ${
                  isActive(link.to)
                    ? "text-foreground"
                    : "text-muted-foreground"
                }`}
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}

function SearchInput() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (location.pathname === "/search") {
      setQuery(searchParams.get("q") || "");
      return;
    }

    setQuery("");
  }, [location.pathname, searchParams]);

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }

    navigate(`/search?q=${encodeURIComponent(trimmedQuery)}`);
  };

  return (
    <form onSubmit={onSubmit} className="flex items-center gap-2">
      <Input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search teams, players, events, matches..."
        autoComplete="off"
      />
      <Button
        type="submit"
        variant="outline"
        size="sm"
        className="cursor-pointer"
      >
        <Search className="h-4 w-4" />
      </Button>
    </form>
  );
}
