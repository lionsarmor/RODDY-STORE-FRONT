LINK COMMANDER — THIN FDM SNAP-LID CASES — FIRST PRINT, 4 NOVEMBER 2026

Print the files ending -PRINT.stl. Units are millimetres. They are already oriented
on the print bed. Each case uses a tray plus a sliding lid that clicks shut.
STEP files and the editable CadQuery generator are included.

CASE SIZES (width x length x height; external plugs and cables excluded)
  Dongle, captured plug: 24.2 x 56.1 x 16.4 mm
  Dongle, short cable:  24.2 x 49.3 x 16.4 mm
  Through-hole dual:   76.2 x 79.3 x 21.4 mm

PRINT SETUP
  PETG recommended for the flexible latch; ordinary PLA is suitable for a first
  dimensional check but is less forgiving of repeated latch flexing.
  Starting point: 0.4 mm nozzle, 0.2 mm layers, 4 perimeters, 25–35% infill.
  Floor, lid and main walls: 1.6 mm. Engraved lettering leaves 1.35 mm of lid.
  Print the base floor down. The lid files put the outer roof face on the bed,
  so its skirts and latch hook grow upward. No supports on the sliding surfaces.
  The USB opening has a short bridge; tune bridging or add local removable
  support there if required by your printer. Do not scale the entire model.
  Print the fit-tests/slide-snap pair first. Sliding clearance is nominally
  0.2 mm per mating side. Remove elephant's foot and strings before evaluating.

ASSEMBLY AND RETENTION
  1. Assemble and electrically inspect the board first. Remove any solder spikes;
     the CAD includes connector tails projecting approximately 2.2 mm below PCB.
  2. Cable cases: feed jacketed cable through the rear hole before soldering.
     Nominal cable OD is 4.0 mm; exit bore is 4.4 mm. Fit a small cable tie around
     the jacket inside the two anchor cheeks; route it through the anchor slots.
     The tie must restrain the jacket, not the individual signal conductors.
     Cable type, tie choice and pull resistance require a physical check.
  3. Insert USB end first into its opening, then lower the rear of the PCB onto
     the side ledges. No PCB mounting holes or screws are required.
  4. Slide the lid in from the USB end. Its long skirts cover the PCB edges,
     while the tongues engage the tray grooves. Slide until the latch clicks.
     The shallow U-shaped tongue near the USB end is the release: gently lift
     its tip with a fingernail or thin plastic tool while sliding the lid out.
     Do not push the release tongue down onto the USB socket.
  5. Open the lid for programming; the existing bare ICSP pads remain accessible.

DIRECT PS/2 NOSE — USER-APPROVED NOMINAL PLUG FIT
  This is a real six-pin MINI-DIN male insert plus a printed holder, not a printed
  electrical connector and not a full-size six-pin DIN plug. It is not a male
  right-angle PCB connector. Four short insulated wires join the plug to J2.
  The tray's front lip, rear stop and side cradle capture the insert; the lid
  closes the cradle. The case carries insertion/pull loads rather than the
  solder joints. The PCB is retained separately by its edge ledges and lid.

  Nominal shield diameter: 9.5 mm; exposed mating length beyond case: 6.5 mm.
  Assumed insert/body envelope inside the holder: 12 x 9 x 11 mm.
  Body clearance: approximately 0.25 mm per side, with an axial clearance.
  These are a common PS/2 mating envelope plus a provisional internal insert
  shape, not a verified internal drawing of a specific supplier's complete plug.
  A complete Kycon KMDLAX cable plug is about 50 mm long and DOES NOT drop into
  this pocket intact. Its cable backshell is for the cable variant. For the
  direct nose, use an appropriately retained insert; adjust this pocket after
  inspecting the actual parts. The two halves must close without crushing the
  pin insulator. Test full seating, polarity key, retention and rotation first.
  The original KiCad concept plug placement remains a historical preview;
  use the new enclosure assemblies for the enclosure's plug position.

STACKED PS/2 PORTS / X16 KIT
  The 16.4 mm dongle height is based on the actual board component models, not
  a guessed X16 socket height. Two identical aligned cases need at least 16.4 mm
  vertical centre pitch geometrically, or 17.0 mm allowing 0.6 mm between them.
  This is a REQUIREMENT of this print, not a measured X16 specification.
  Hold fit-tests/dongle-height-gauge-PRINT.stl in front of the sockets to check
  the envelope. It has a registration hole, not electrical pins. Keep the X16
  powered off during plug-fit checks. Check the adjacent plug's body too.
  TexElec presents the current build kit as the Developer Edition kit; no
  separate, verified socket-centre drawing was obtained for each revision.
  The cable version avoids mounting the case between stacked socket bodies and
  accommodates differing socket/case layouts. The dual always uses two leads.

ELECTRICAL CONNECTIONS (unchanged)
  J2 pad 1 = DATA -> mini-DIN contact 1
  J2 pad 2 = GND  -> mini-DIN contact 3
  J2 pad 3 = +5V  -> mini-DIN contact 4
  J2 pad 4 = CLK  -> mini-DIN contact 5
  J102 uses the same mapping for the mouse channel. Never join the dual's two
  +5V rails. Use contact continuity, not cable colours, to identify conductors.

PROGRAMMER
  Recommended: genuine Microchip PICkit 5 PG164150, Mouser 579-PG164150.
  https://www.mouser.com/ProductDetail/Microchip-Technology/PG164150
  MPLAB IPE provides a graphical device / tool / HEX-file / Program workflow.
  One tool programs the dongle MCU and each of the dual's two MCUs individually.
  Use our documented 3.3 V ICSP connections and a current-limited powered fixture;
  leave programmer target-power output OFF. Firmware is still to be developed.
  https://www.microchip.com/en-us/development-tool/pg164150

VALIDATION / LIMITS
  CAD-CHECKS.json: valid single-solid tray/lid, no static electronics collisions.
  PRINT-CHECKS.json: manifold print meshes and sampled rigid lid insertion path.
  The flexible latch hook is excluded from rigid-motion tests because it must
  deflect to latch. Physical snap force, fatigue, printed clearances, plug fit,
  cable pull resistance, USB-receiver body clearance and temperature are not
  certified by CAD. No circuit, copper, PCB outline or component placement changed.
  These files are complete first-fit print models, not a production qualification.
