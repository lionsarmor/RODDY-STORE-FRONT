# Private electronics project wizard

Open **Admin → Electronics / PCBWay**. The four steps collect the project and
build method, board ZIP, assembly/extras, then prototype/customer shipping.
**I'll assemble it myself** requires the manufacturing ZIP only. Factory assembly
also needs a BOM; SMT/mixed assembly needs positions. Through-hole-only assembly
does not require positions. Optional files include assembly drawings, firmware,
test instructions, enclosure geometry and box-build notes.

**Ship prototypes to me** accepts an owner address and can remember it privately.
**Ship to the customer** prepares a delivery template; a future fulfillment
adapter must take the actual address from a verified paid order. It does not use
the owner's prototype address for customer shipments. Blank board dimensions mean
unknown and must be resolved during engineering review.

Projects and raw files live under `PCB_PROJECTS_DIR`, defaulting to the actual
orders database's parent plus `pcb-projects`. Directories are 700, files 600.
The existing owner authorization protects listing, updates, uploads and exports.
Files never go to GitHub, the public media library, or a supplier. Uploads stream
with a 20 MB file limit and 128 MB project limit; archives are checked and never
extracted. Export verifies stored SHA-256 values and deletes its temporary ZIP
after sending it. Include the project directory in private backups.

The exported `PROJECT_MANIFEST.json` is a versioned internal adapter contract:
project/revision, build scope, component sourcing, board specs, file roles and
hashes, testing/packaging notes, and prototype or paid-order delivery policy.
`automation.submit` and `automation.pay` are false. "Ready for engineering review"
means the selected file categories are present, not that the design is approved
or that a fabrication quote has passed.

PCBWay's official [assembly file guide](https://www.pcbway.com/assembly-file-requirements.html)
specifies Gerbers, BOM and centroid data, with drawings recommended. Its
[partner API help](https://api-partner.pcbway.com/Help) lists PCB quotation,
shipping, order/payment/status interfaces and an SMT quotation endpoint. The help
page describes a test environment; production credentials, assembly scope,
prototypes, repeat fulfillment, billing and customer dispatch must be verified
with the supplier before connecting live submission. This change implements the
private wizard and package contract, not supplier ordering or payment.

The Caddy store site gives only the authenticated upload path a 20 MB body limit;
other API requests retain a 256 KB proxy ceiling and stricter application limits.
Validate and reload Caddy when installing this route. Keep the rest of the existing
Caddyfile and unrelated services unchanged.
