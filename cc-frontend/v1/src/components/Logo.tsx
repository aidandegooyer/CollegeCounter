import logo from "@/assets/0.1x/C Logo@0.1x.png";
import sillhouette from "@/assets/player_silhouette.png";

interface LogoProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  type: "player" | "team";
}

function Logo(props: LogoProps) {
  const handleError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    const fallback = props.type === "player" ? sillhouette : logo;
    if (e.currentTarget.src !== fallback) {
      e.currentTarget.src = fallback;
    }
  };

  return (
    <img
      src={props.src}
      className={`h-8 w-8 ${props.className || ""}`}
      alt="Logo"
      onError={handleError}
      {...props}
    />
  );
}

export default Logo;
