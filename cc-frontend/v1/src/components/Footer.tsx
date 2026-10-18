import { NavLink } from "react-router";
import logo from "../assets/0.1x/C Logo@0.1x.png";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "https://api.collegecounter.org/v1";
// The commit this was built from, set by scripts/deploy-prod.sh. The API docs show
// the same commit in their version (e.g. 1.0.0+8f03a25).
const BUILD_SHA = import.meta.env.VITE_BUILD_SHA || "dev";

const linkClass =
  "text-muted-foreground hover:text-foreground transition-colors";

function Footer() {
  return (
    <footer className="mx-auto max-w-[1200px] px-4 pt-8 pb-10">
      <div className="border-t pt-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2">
            <NavLink to="/" className="flex w-fit items-center gap-2">
              <img src={logo} alt="" className="h-6 w-6 rounded-sm" />
              <span className="font-block text-muted-foreground text-xl">
                College Counter
              </span>
            </NavLink>
            <p className="text-muted-foreground text-sm">
              Created by aidanxi, sensh1, and Kimmer-, with thanks to our
              community volunteers.
            </p>
          </div>

          <nav aria-label="Footer">
            <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
              <li>
                <NavLink to="/privacy-policy" className={linkClass}>
                  Privacy Policy
                </NavLink>
              </li>
              <li>
                <a href={`${API_BASE_URL}/public/docs/`} className={linkClass}>
                  API Docs
                </a>
              </li>
              <li>
                <NavLink to="/admin" className={linkClass}>
                  Admin
                </NavLink>
              </li>
            </ul>
          </nav>
        </div>

        <div className="text-muted-foreground/70 mt-8 flex flex-col gap-3 text-xs sm:flex-row sm:items-end sm:justify-between sm:gap-8">
          <p className="max-w-2xl">
            &copy; {new Date().getFullYear()} Station XI LLC. College Counter is
            not affiliated with or endorsed by Valve Corporation, FACEIT, or any
            college, university, or league. Counter-Strike is a trademark of
            Valve Corporation. All other trademarks and logos belong to their
            respective owners.
          </p>
          <p className="shrink-0 font-mono">
            {BUILD_SHA === "dev" ? (
              "dev build"
            ) : (
              <a
                href={`https://github.com/aidandegooyer/CollegeCounter/commit/${BUILD_SHA}`}
                className="hover:text-foreground transition-colors"
              >
                build {BUILD_SHA}
              </a>
            )}
          </p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
