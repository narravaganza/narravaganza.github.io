# Frame experiments

The collection uses a controller in `assets/js/collection-frames.js` and a procedural canvas renderer in `assets/js/collection-frame-worker.js`, loaded only by the fine-art collection layout. Every `.collection-frame` gets a carved relief built as a height field: deep cove mouldings, interwoven geometric ribbons, chased seals, engine-turned corner cartouches, twisted borders, gadroons, pearl beading and engraved fillets. Edges stay straight; there are no floral ornaments or serrations. No downloaded frame assets are used.

The `finishes` table pairs each artwork with a sympathetic gold/pewter palette, moulding width, engraving and relief depth. Every work receives the full intricate carving; Monet, Degas and Van Gogh retain particularly broad surrounds. Surface normals drive directional lighting and metallic highlights. Seeded gold-leaf variation, fine surface wrinkles and darker recesses break up the finish without changing each frame's identity across reloads.

`IntersectionObserver` queues frames within 400px of the viewport. One worker shades one frame at a time using `OffscreenCanvas`, then transfers the completed bitmap to the page. `ResizeObserver` queues only nearby frames; offscreen frames use their latest dimensions when they return. Outdated bitmaps are discarded after a resize. Rendering uses up to 1.5× resolution. Only border pixels are shaded; the opening is transparent. The painting remains an ordinary responsive image with its original aspect ratio and alt text. The canvas is decorative and hidden from assistive technology.

Frame widths and responsive moulding thickness live in `assets/css/styles.scss`. Without JavaScript, worker canvas support, or a working renderer, the CSS supplies a simple gilt surround.
