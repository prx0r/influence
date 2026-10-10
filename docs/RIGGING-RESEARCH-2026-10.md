# Rigging & motion research — 2026-10-10 (character factory)

> Saved from research brief. Pogtown/Freaktown character pipeline:
> mesh → rig → animate → face → stage → MP4. Rent capabilities, own evidence.

## Stage table

| Stage | Strongest candidates |
|---|---|
| Identity/appearance | Pogpet/Meshy, AssetFurnace |
| Skeletal rigging | **Tripo API** (7 creature classes), SkinTokens, AniGen |
| Rig validation | Autorig Workbench, Blender |
| Reusable animation | Mesh2Motion, Mixamo |
| AI motion for arbitrary rigs | **UniMate** (bring-your-own-rig Oct 5), MoCapAnything |
| Facial blendshapes | QtMeshEditor (humanoids, 52 ARKit, CLI+MCP); custom jaw/eyes for animals |
| Voice-driven face | TalkingHead, Rhubarb, Audio2Face |
| Rendering/directing | Freaktown StageRuntime (ours) |
| Film tooling | fframes, filmcraft |

## Key findings

- **UniMate** (SIGGRAPH Asia 2026, ~1.7k★, BYO-rig Oct 5): text→motion for diverse skeletons, 13k+ paired motions. Test as optional clip source AFTER GLB player works.
- **AniGen** (VAST): image→mesh+skeleton+skin in one pass. 18GB VRAM (rented compute). SkinTokens when we like the Meshy geometry (14GB).
- **Tripo v2.5 vs Meshy API**: Meshy API says non-humanoid rigs unsuitable; **Tripo supports quadrupeds/birds/etc via API**. For Nolan (dog) → Tripo is the API path.
- **QtMeshEditor Face Rig** (Oct 9): 52 ARKit shapes from neutral face, no GPU, CLI+MCP, numeric quality gate. Humanoid only; glTF blendshape export bug to fix. Start with jaw+eyes+brow+5-8 expressions instead of all 52.
- **Iki** (MIT, Oct 10): 2D puppet for AI agents (blink/mouth/gaze/breath), MCP server. Cheap alternative for podcast/news formats — don't abandon 3D, but good for quick format experiments.
- **AssetFurnace** (Oct 10, v0.4.3): image/prompt→textured 3D character + rig + animation, established history. Could be character factory part.

## First Pogtown minute (trial stack)

1. Existing Pogpet/Meshy GLB (don't regenerate)
2. **Tripo v2.5 quadruped rig** (alt: Mesh2Motion/SkinTokens)
3. Rigged GLB + idle/gesture clips + simple facial controls + Freaktown delivery timeline
4. Extend Three.js runtime for non-VRM GLB + animation → vertical MP4
5. Proof: speaks, blinks, reacts, gestures, holds punchline pause, synced, 60s set

**Rule:** test Tripo+UniMate for animal pipeline; integrate UniMate only after GLB player works; small expressive face rig > full ARKit 52.

## Licences to check
- MoCapAnything code MIT, animal-motion data separate licence
- ARKitRemap: UE5.8-dependent + restricted — study curves only, don't add Unreal
- Iki: MIT
