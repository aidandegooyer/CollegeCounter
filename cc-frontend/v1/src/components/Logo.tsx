import logo from "@/assets/cs2 guy.png";
import sillhouette from "@/assets/player_silhouette.png";
import cc from "@/assets/0.5x/C Logo@0.5x.png";

interface LogoProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  type: "player" | "team" | "cc";
}

function Logo(props: LogoProps) {
  if (props.type == "cc") {
    return (
      <img
        src={cc}
        className={`${props.className || ""}`}
        alt="Logo"
        {...(props.onClick && { onClick: props.onClick })}
        {...(props.style && { style: props.style })}
      />
    );
  }

  const fallback = props.type === "player" ? sillhouette : logo;
  const handleError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    const fallback = props.type === "player" ? sillhouette : logo;
    if (e.currentTarget.src !== fallback) {
      e.currentTarget.src = fallback;
    }
  };
  if (
    !props.src ||
    props.src.trim() === "" ||
    props.src === "undefined" ||
    props.src === "null"
  ) {
    return (
      <img
        src={fallback}
        className={`${props.className || ""}`}
        alt="Logo"
        {...(props.onClick && { onClick: props.onClick })}
        {...(props.style && { style: props.style })}
      />
    );
  }

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
