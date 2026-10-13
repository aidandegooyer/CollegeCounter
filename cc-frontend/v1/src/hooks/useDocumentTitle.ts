import { useEffect } from "react";

const SITE_NAME = "College Counter";

// Sets the browser tab title while the page is shown, e.g. "Rankings" →
// "Rankings - College Counter". Pass nothing (or nothing yet, while the page
// loads) for just the site name. Resetting on unmount stops the title from
// sticking on the next page.
export function useDocumentTitle(title?: string | null) {
  useEffect(() => {
    document.title = title ? `${title} - ${SITE_NAME}` : SITE_NAME;
    return () => {
      document.title = SITE_NAME;
    };
  }, [title]);
}
