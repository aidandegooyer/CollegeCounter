
// Define TypeScript types for Sanity Blog Posts
interface SanityImage {
    _type: "image";
    asset: {
      _type: "reference";
      _ref: string;
    };
  }
  
interface PortableTextBlock {
    _type: "block";
    _key: string;
    style?: string;
    markDefs?: { _key: string; _type: string; href?: string }[];
    children: { _type: "span"; text: string; _key: string; marks?: string[] }[];
}

interface SanityPost {
_id: string;
title: string;
slug: { _type: "slug"; current: string };
body: PortableTextBlock[];
image?: SanityImage;
author?: string;
authorLink?: string;
publishedAt: string;
}



export type { SanityPost, PortableTextBlock, SanityImage };