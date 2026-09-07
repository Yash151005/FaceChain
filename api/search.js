const MAX_IMAGE_BYTES = 500 * 1024;

function extractMatch(results) {
  const visualMatches = Array.isArray(results.visual_matches) ? results.visual_matches : [];
  for (const item of visualMatches) {
    const url = item.link || item.url;
    if (isPublicUrl(url)) {
      return {
        url,
        title: item.title || "Public visual match",
        domain: getDomain(url) || item.source || "Unknown source",
        thumbnail: item.thumbnail || null,
      };
    }
  }

  const graph = results.knowledge_graph;
  const graphUrl = graph?.link || graph?.source?.link;
  if (isPublicUrl(graphUrl)) {
    return {
      url: graphUrl,
      title: graph.title || "Knowledge graph match",
      domain: getDomain(graphUrl),
      thumbnail: graph.thumbnail || null,
    };
  }

  const organic = Array.isArray(results.organic_results) ? results.organic_results : [];
  for (const item of organic) {
    if (isPublicUrl(item.link)) {
      return {
        url: item.link,
        title: item.title || "Public search result",
        domain: getDomain(item.link),
        thumbnail: item.thumbnail || null,
      };
    }
  }

  return null;
}

function isPublicUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}

function getDomain(value) {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch {
    return "Unknown source";
  }
}

function parseImage(dataUrl) {
  const match = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/.exec(dataUrl || "");
  if (!match) throw new Error("Upload a JPG, PNG, or WebP image.");
  const bytes = Buffer.from(match[2], "base64");
  if (!bytes.length || bytes.length > MAX_IMAGE_BYTES) {
    throw new Error("The prepared image must be smaller than 500 KB.");
  }
  return { bytes, mime: match[1] };
}

export default async function handler(request, response) {
  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    return response.status(405).json({ error: "Method not allowed." });
  }

  const apiKey = process.env.SERPAPI_KEY;
  if (!apiKey) return response.status(503).json({ error: "Reverse search is not configured." });

  try {
    const { bytes, mime } = parseImage(request.body?.image);
    const form = new FormData();
    form.append("api_key", apiKey);
    form.append("image", new Blob([bytes], { type: mime }), `face.${mime.split("/")[1]}`);

    const uploadResponse = await fetch("https://serpapi.com/image", { method: "POST", body: form });
    const upload = await uploadResponse.json();
    if (!uploadResponse.ok || !upload.image_id) {
      throw new Error(upload.error || "SerpAPI could not accept this image.");
    }

    const params = new URLSearchParams({
      engine: "google_lens",
      image_id: upload.image_id,
      api_key: apiKey,
    });
    const searchResponse = await fetch(`https://serpapi.com/search.json?${params}`);
    const results = await searchResponse.json();
    if (!searchResponse.ok || results.error) {
      throw new Error(results.error || "Reverse search did not complete.");
    }

    const match = extractMatch(results);
    if (!match) return response.status(404).json({ error: "No public visual match was found. Try a clearer image." });
    return response.status(200).json(match);
  } catch (error) {
    return response.status(400).json({ error: error.message || "Reverse search failed." });
  }
}
