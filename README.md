# CE Realistic Autocannon Explosions

![Patched autocannon explosion radii](graph.webp)

One RimWorld cell is one metre of fragment-danger radius.

| Projectile ID              | CE damage | IRL TNT (g) | Radius (cells) |
| -------------------------- | --------: | ----------: | -------------: |
| Bullet_20x102mmNATO_HE     |        31 |        10.7 |           1.64 |
| Bullet_20x110mmHispano_HE  |        35 |           6 |           1.45 |
| Bullet_20x128mmOerlikon_HE |        35 |          10 |           1.61 |
| Bullet_20x138mmB_HE        |        35 |          11 |           1.66 |
| Bullet_20x139mm_HE         |        35 |          10 |           1.61 |
| Bullet_20x82mmMauser_HE    |        33 |           6 |           1.45 |
| Bullet_20x99mmRShVAK_HE    |        31 |           4 |           1.37 |
| Bullet_23x115mm_HE         |        44 |          15 |           1.82 |
| Bullet_23x152mmB_APHE      |        46 |          18 |           1.94 |
| Bullet_25x137mmNATO_HE     |        45 |          22 |            2.1 |
| Bullet_27x145mmMauser_HE   |        56 |          20 |           2.02 |
| Bullet_30x113mmB_HE        |        58 |          24 |           2.19 |
| Bullet_30x165mm_HE         |        71 |          49 |           3.21 |
| Bullet_30x170mm_HE         |        68 |          38 |           2.76 |
| Bullet_30x173mmNATO_HE     |        69 |          44 |              3 |
| Bullet_35x228mmNATO_HE     |        87 |         112 |           5.78 |
| Bullet_40x311mmR_HE        |       117 |          90 |           4.88 |

Run: deno run --allow-read --allow-write --allow-run=magick scripts/generate.ts
[CE defs path].
