# Source material

Raw material for the site. Not published as-is – the pages paraphrase it.

## The friend's response (author's own update, published on Reddit)

**Important: this is the author's account, not the friend's direct words.**
It must never be presented on the site as a quote attributed to the friend.

> A lot of people asked for an update, so here it is :)
>
> Of course, my friend really liked it. When he saw the map, he was genuinely
> moved and cried.
>
> He spends a lot of time with it, but honestly, the part he liked most was
> Braille itself. He had wanted to learn it for a long time, but he had never
> really had an opportunity.
>
> So now we spend time together, and I teach him how to read Braille. It is
> difficult for him, but he really enjoys trying and puts a lot of effort and
> energy into it. And he keeps thanking me for being patient with him.
>
> At the same time, there are quite a few problems with the map itself that I
> discovered while using it with him.
>
> First, I used regular raised numbers on the map instead of numbers written in
> Braille. That is, of course, a downside.
>
> Second, the dots on the Braille alphabet came out quite small and sharp, so
> they are difficult to distinguish.
>
> I tried to use standard Braille dimensions and spacing, but after 3D printing,
> the result was not quite what I expected. Everything looked normal in the
> model, but by touch, the dots were not as comfortable or easy to distinguish.
>
> Because of that, learning is more difficult for him, since the dots themselves
> are hard to tell apart. But he is trying very hard, and he is already making
> progress.
>
> I think that in the second version of the map, I will take all of these
> problems into account and make it better.

### What this is worth, in order

1. He wanted to learn braille for years and never had the chance – the map
   became the reason he started. This is the strongest thing in the story.
2. He was moved to tears when he received it.
3. They now practise together; it is hard, and he is making progress.
4. Using it together exposed two real defects, and both were fixed.

## Both defects are already fixed in the current code

| Defect in the printed v1 | Current state (`core/`) |
|---|---|
| Plain raised numerals on the map, not braille | `create_braille_number()` in `generate.py` |
| Braille dots small and sharp, hard to tell apart | `create_braille_dot()` – smooth dome on a buried skirt: ⌀1.6 mm, 0.8 mm tall, 2.5 mm dot pitch, 6.0 mm cell pitch |

So every photograph on this site shows **v1**, while every render shows the
**current** version. Nothing on the page may blur that line.

## Reddit history (all published before the site existed)

- https://www.reddit.com/r/somethingimade/comments/1umi0md/i_made_a_tactile_3d_map_for_my_blind_friends/
- https://www.reddit.com/r/somethingimade/comments/1v23a09/update_i_gave_the_tactile_map_to_my_blind_friend/
- reposted in r/BestofRedditorUpdates:
  https://www.reddit.com/r/BestofRedditorUpdates/comments/1vfwkrv/comment/p1tdl3i/

## Asset inventory

Sources: `blind_map/data/photoes/` (photos), `blind_map/data/output/previews_v2/`
(renders), `blind_map/data/output/makerworld/` (sliced 3MF + STLs).

Renders on the site were re-made on 2026-08-05 from the *current* STLs
(`render_previews.py`); the previous set predated the removal of the capital
bumps and still showed one.

| Asset | State |
|---|---|
| Hands on the assembled map | on the site (`hands_map.jpg`) |
| Blind reader, both hands on the map | on the site (`reader.jpg`) |
| Full set of six printed pieces | on the site (`set.jpg`) |
| Author portrait | on the site (`author.jpg`) |
| Raised numerals on the printed v1, cropped from `photo_12` | on the site (`first_print_numbers.jpg`), the "before" half of the comparison |
| Same corner of the map from the current files, braille labels | on the site (`render_labels.jpg`), the "after" half |
| Studio renders (label macro, terrain steps, joint, legend, all plates) | on the site |
| Assembled iso render | dropped: too small in frame, superseded by the two macros |
| Friend's response | this file |
| Sliced `.3mf`, 8 plates | exists, for MakerWorld |
| Hero video | **missing** |
| Photos of the reprinted v2 | **missing** |
| Close shot of a finger reading a braille cell | **missing** – braille cards appear in `photo_2` and `photo_3`, but no frame shows a finger on the dots |
| Friend's words in his own voice | not planned – the paraphrase above stands in |
