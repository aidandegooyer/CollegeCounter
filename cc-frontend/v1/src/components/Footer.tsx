import { NavLink } from "react-router";

function Footer() {
  return (
    <div className="mx-auto max-w-[1200px] p-4">
      <hr />
      <footer className="footer">
        <div className="container mx-auto p-4 text-center">
          <p className="text-muted-foreground text-sm">
            Created by aidanxi, sensh1, and Kimmer-
          </p>

          <p className="text-muted-foreground text-sm">
            &copy; {new Date().getFullYear()} Station XI LLC
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <NavLink
              to="/admin"
              className="text-muted-foreground text-sm underline"
            >
              Admin Panel
            </NavLink>

            <NavLink
              to="/privacy-policy"
              className="text-muted-foreground text-sm underline"
            >
              Privacy Policy
            </NavLink>
          </div>
          <p className="text-muted-foreground mt-2 text-xs italic">
            Thank you to our community volunteers for their contributions ♥
          </p>
        </div>
      </footer>
    </div>
  );
}

export default Footer;
