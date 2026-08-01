# CE Realistic Autocannon Explosions

![Patched autocannon explosion radii](graph.webp)

One RimWorld cell is one metre of fragment-danger radius. The graph shows every
patched projectile and its radius change from zero.

| Projectile                 | HE filler (g) | Radius (cells) |
| -------------------------- | ------------: | -------------: |
| Bullet_20x102mmNATO_HE     |          10.7 |           1.64 |
| Bullet_20x110mmHispano_HE  |             6 |           1.45 |
| Bullet_20x128mmOerlikon_HE |            10 |           1.61 |
| Bullet_20x138mmB_HE        |            11 |           1.66 |
| Bullet_20x139mm_HE         |            10 |           1.61 |
| Bullet_20x82mmMauser_HE    |             6 |           1.45 |
| Bullet_20x99mmRShVAK_HE    |             4 |           1.37 |
| Bullet_23x115mm_HE         |            15 |           1.82 |
| Bullet_23x152mmB_APHE      |            18 |           1.94 |
| Bullet_25x137mmNATO_HE     |            22 |            2.1 |
| Bullet_27x145mmMauser_HE   |            20 |           2.02 |
| Bullet_30x113mmB_HE        |            24 |           2.19 |
| Bullet_30x165mm_HE         |            49 |           3.21 |
| Bullet_30x170mm_HE         |            38 |           2.76 |
| Bullet_30x173mmNATO_HE     |            44 |              3 |
| Bullet_35x228mmNATO_HE     |           112 |           5.78 |
| Bullet_40x311mmR_HE        |            90 |           4.88 |

Run: deno run --allow-read --allow-write --allow-run=magick scripts/generate.ts
[CE defs path].
