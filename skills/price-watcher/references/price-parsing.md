# Price Parsing

Extract prices conservatively. Do not record a price unless it is visible or present in structured product offer data.

## Currency

Recognize common symbols:

- `$` -> infer USD/CAD/AUD from site or user locale
- `US$` -> USD
- `CA$` -> CAD
- `£` -> GBP
- `€` -> EUR

Store ISO-style currency codes when possible.

## Parsing Rules

- Remove thousands separators.
- Preserve cents.
- Ignore crossed-out list prices when a current sale price is visible.
- Ignore monthly financing prices unless the product is normally sold as a subscription.
- Ignore cart, checkout, or member-only prices if they require an account, cart action, or bypassing access controls.
- If a page shows a range, report the range in Markdown and store the lowest visible price only when it is a valid purchasable price.

## Preferred Extraction Order

1. JSON-LD `Product.offers.price` and `priceCurrency`
2. meta tags such as `product:price:amount`
3. embedded page state JSON with offer data
4. visible DOM text near the product title, price block, or buy box
