import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "60vh",
        textAlign: "center",
      }}
    >
      <h1>404</h1>
      <p>Sorry, the page you are looking for does not exist.</p>
      <Link to="/" className="underline transition-colors hover:text-blue-400">
        Go back to Home
      </Link>
    </div>
  );
}
