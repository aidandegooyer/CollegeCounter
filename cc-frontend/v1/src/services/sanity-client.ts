import { createClient } from '@sanity/client';

const client = createClient({
  projectId: "lpn0asci",
  dataset: "production",
  apiVersion: "2025-08-13",
  useCdn: false, // `false` if you want fresh data
});

export default client;