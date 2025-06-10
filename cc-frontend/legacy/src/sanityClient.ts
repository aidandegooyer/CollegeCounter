import { createClient } from '@sanity/client';

const client = createClient({
  projectId: "lpn0asci",
  dataset: "production",
  apiVersion: "2024-01-01",
  useCdn: true, // `false` if you want fresh data
});

export default client;