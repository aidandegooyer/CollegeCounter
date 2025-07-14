import { Input } from "./ui/input";
import logo from "../assets/0.1x/C Logo@0.1x.png";

function Navbar() {
  return (
    <nav className="px-4 py-3 w-full">
      <div className="container flex justify-between items-center max-w-[1200px] mx-auto">
        <div className="flex items-center">
          <img
            src={logo}
            alt="College Counter Logo"
            className="h-10 w-10 mr-2"
          />
          <div className="text-2xl font-bold">College Counter</div>
        </div>
        <ul className="flex space-x-6">
          <li>
            <a
              href="/"
              className="hover:text-blue-200 text-muted-foreground transition-colors"
            >
              Rankings
            </a>
          </li>
          <li>
            <a
              href="/"
              className="hover:text-blue-200 text-muted-foreground transition-colors"
            >
              Matches
            </a>
          </li>
          <li>
            <a
              href="/about"
              className="hover:text-blue-200 text-muted-foreground transition-colors"
            >
              Results
            </a>
          </li>
          <li>
            <a
              href="/contact"
              className="hover:text-blue-200 text-muted-foreground transition-colors"
            >
              Events
            </a>
          </li>
        </ul>
        <div>
          <Input placeholder="Search" />
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
