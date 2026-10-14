# Private supplier mappings

The current public catalog contains retail content, available options, shipping
estimates and opaque `fulfillmentRef` versions. Exact supplier/store/listing/SKU
mappings live in `CATALOG_SOURCING`, defaulting beside the order database as
`catalog-sourcing.json`, mode 600. The checkout server hydrates the exact referenced
mapping before quoting or freezing an order. Missing versions fail closed.

Admin GitHub catalog reads hydrate mappings through owner-authenticated
`GET /admin/catalog-sourcing`. Publication saves an immutable mapping version on
the droplet first, then writes the sanitized catalog to GitHub. A failed GitHub
write cannot switch an existing public product to the newly staged mapping.
Retail prices and availability still come from the public catalog; private
mapping data cannot silently replace the owner's current retail edits.

Current option photos are local assets. Future merchandise publishing copies
approved image-host files through an authenticated, bounded, non-redirecting
image reader, then uploads them through the existing media publisher. Supplier
references, raw errors and fulfillment kinds do not enter customer receipts.
The legacy public manufacturer packet is no longer served.

Back up the mapping file privately with orders and credentials. Paid order
snapshots remain self-contained and unaffected by mapping or catalog changes.
This change does not rewrite the public repository's historical commits or
previously downloaded/cached copies of its older catalog and assets.
