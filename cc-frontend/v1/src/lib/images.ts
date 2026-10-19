// Team/player/event pictures stored by the backend (cc-backend/v1/cc/images.py)
// come in fixed sizes at .../<hash>/<width>.webp, and the API returns the
// 512px one. Pictures hosted elsewhere don't match and are used as they are.
const STORED_PICTURE = /^(.*\/[0-9a-f]{12}\/)(64|128|256|512)\.webp$/;
const PICTURE_WIDTHS = [64, 128, 256, 512];

// Whether `url` is one of our stored copies. The CDN sends CORS headers for
// them, so they can be drawn into a canvas without the backend proxy.
export function isStoredPicture(url: string) {
  return STORED_PICTURE.test(url);
}

// srcset of every stored size, or undefined for pictures hosted elsewhere
export function pictureSrcSet(url: string | null | undefined) {
  const match = url?.match(STORED_PICTURE);
  if (!match) return undefined;
  return PICTURE_WIDTHS.map(
    (width) => `${match[1]}${width}.webp ${width}w`,
  ).join(", ");
}

// Displayed size, in px, of an element sized by Tailwind h-N classes (the
// largest one, so responsive variants like "h-16 md:h-32" stay sharp)
export function tailwindHeightPx(className: string | undefined) {
  const heights = [
    ...(className ?? "").matchAll(/(?:^|[\s:])h-(\d+)(?=\s|$)/g),
  ];
  if (heights.length === 0) return undefined;
  return Math.max(...heights.map((match) => Number(match[1]) * 4));
}

// Sanity's image CDN resizes and converts on request
const SANITY_CDN = "https://cdn.sanity.io/images/";
const SANITY_WIDTHS = [400, 800, 1200];

function sanityImageUrl(url: string, width: number) {
  // fit=max never enlarges; auto=format serves WebP/AVIF where supported
  return `${url}${url.includes("?") ? "&" : "?"}w=${width}&fit=max&auto=format`;
}

// src/srcSet/sizes for an <img>; non-Sanity URLs pass through as src
export function sanityImageProps(url: string | undefined, sizes: string) {
  if (!url?.startsWith(SANITY_CDN)) return { src: url };
  return {
    src: sanityImageUrl(url, 800),
    srcSet: SANITY_WIDTHS.map(
      (width) => `${sanityImageUrl(url, width)} ${width}w`,
    ).join(", "),
    sizes,
  };
}
