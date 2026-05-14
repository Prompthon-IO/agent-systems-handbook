# Source Discovery And Product Normalization

Discover sources from the product query instead of asking for a URL.

## Search Pattern

Run several searches, mixing broad and retailer-specific queries:

- `"<query>" price`
- `"<query>" buy`
- `"<query>" site:bestbuy.com`
- `"<query>" site:walmart.com`
- `"<query>" site:target.com`
- `"<query>" site:bhphotovideo.com`
- `"<query>" site:amazon.com`

Choose retailers or marketplaces appropriate to the product category and the user's country.

## Normalization

Normalize names before deduplication:

- lowercase
- strip punctuation and marketing suffixes
- normalize units, generations, and sizes
- preserve important attributes such as model, year, processor, storage, dimensions, color, pack size, and condition

Treat these as likely different products unless the page proves equivalence:

- different generation or release year
- different storage or memory
- refurbished vs new
- used/open-box vs new
- bundle vs standalone item
- subscription price vs one-time price

Prefer source URLs that lead to a stable product detail page over search result pages.
