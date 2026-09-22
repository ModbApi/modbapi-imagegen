# Prompt optimization

Use this guidance when a request is long, repetitive, or asks for several consistent views in one image.

## Compression rules

1. Choose one supported aspect ratio before writing the prompt. Do not send alternatives such as "16:9 or 4:3". For five full-body views, prefer `16:9` (`1024x576`); use `4:3` (`1024x768`) when four or fewer views need more vertical detail.
2. Resolve framing alternatives. For example, choose "full body, head and feet visible" instead of "full body or thigh crop" followed by "do not crop feet".
3. State the identity lock once: same adult person, same face, age, skin tone, body proportions, hair, makeup, accessories, and wardrobe in every view; only camera-relative orientation changes.
4. Group wardrobe details once and say that front, side, and back construction remains identical. Avoid repeating each garment property for every angle.
5. Describe anatomy and silhouette once in neutral visual language. Keep requested proportions, but remove repeated emphasis that does not add a new visual constraint.
6. Prefer a short positive composition specification followed by one concise `Avoid:` line. Deduplicate synonymous failures.
7. Do not add labels, captions, numbers, logos, or watermarks unless the user explicitly requests them.

## Five-view character sheet example

Use the following compact structure for a cinematic adult character turnaround. Adapt only details supplied by the user.

```text
真人电影摄影质感的专业角色转面设定板，16:9 横向画布，暖灰色无缝摄影棚背景。同一位成年女性在同一画面中等距排列为五个完整全身视图：正面、左侧面、右侧面、背面、正面三分之二侧身。五人不重叠，头部、双脚和礼服裙摆全部可见；各视图仅改变朝向。

身份锁定：同一位约 25 岁的成年亚洲女性；所有视图保持完全相同的脸部、五官比例、年龄、肤色、高挑匀称的身材比例、自然丰满且协调的 D 罩杯胸部轮廓、肩宽、腰臀比例、微卷长发、妆容、钻石耳饰和细钻项链。气质优雅、冷静、自信，眼神坚定克制，具有豪门短剧女主和高级时装模特质感。

服装锁定：所有视图穿同一件浅香槟色高级缎面晚礼服；端庄合体的时装剪裁，统一的领口、肩部结构、腰线、裙长和背部设计；丝绸缎面反光真实，贴合自然，不透明，不暴露。

姿态与灯光：自然直立，肩膀放松，下巴微抬，双手自然垂放，手指清晰；柔和均匀的电影棚灯和轻微轮廓光，真实皮肤、发丝和礼服材质，高清自然色彩。画面不含文字、编号、标签、Logo 或水印。

Avoid: identity drift, different faces or bodies, changed hair or wardrobe, anatomy or hand errors, distorted gown, inconsistent proportions, overlap, cropping, cluttered background, exaggerated pose, nudity, transparent clothing, excessive cleavage, over-retouching, blur, overexposure.
```

Send this example with `--size 16:9`; the helper normalizes it to `1024x576`.
