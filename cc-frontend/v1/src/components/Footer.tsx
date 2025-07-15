import { NavLink } from "react-router";

function Footer() {
  return (
    <div className="mx-auto max-w-[1200px] p-4">
      <hr />
      <footer className="footer">
        <div className="container mx-auto p-4 text-center">
          <p className="text-muted-foreground text-sm">
            Created by aidanxi and sensh1
          </p>
          <p className="text-muted-foreground text-sm">
            &copy; {new Date().getFullYear()} Station XI LLC
          </p>
          <NavLink
            to="/admin"
            className="text-muted-foreground text-sm underline"
          >
            Admin Panel
          </NavLink>
        </div>
      </footer>
    </div>
  );
}

export default Footer;
