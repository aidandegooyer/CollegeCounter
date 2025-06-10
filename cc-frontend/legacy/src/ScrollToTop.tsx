import { useEffect } from "react";
import { useLocation } from "react-router";

export default function ScrollToTop() {
  const { key } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [key]);

  return null;
}
