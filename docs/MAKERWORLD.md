# MakerWorld — готовый пакет для загрузки

Всё ниже — копипаста в форму загрузки MakerWorld.

Сами файлы собираются командой `python core/export_3mf.py` в
**`data/output/makerworld/`** (как и весь остальной вывод сборки, в гит не
попадает). Имена там уже человекочитаемые — MakerWorld показывает их
посетителям.

---

## Model Name (лимит 50 символов!)

```
Tactile Braille Map for the Blind: Europe & Arabia
```

Ровно 50 символов — впритык, ни одного лишнего не добавляй.
Ключевики: tactile / braille / map / blind / europe / arabia.
Запасной вариант на 49, если форма ругнётся на длину:
«Braille Tactile Map for the Blind: Europe, Arabia»

⚠️ **Слово «Europe» в одиночку в заголовке не ставим.** `MAP_BOUNDS` в
`core/config.py` — это 5–70° в.д., 12–55° с.ш. Франции, Испании, Британии и
Скандинавии на карте нет вообще, зато есть Саудовская Аравия, Йемен, Оман,
Судан и Афганистан: 13 из 27 подписанных стран — не европейские. Листинг
«Map of Europe», где покупатель не находит Францию, но находит Йемен, —
это комментарии «это не Европа» и минус к рейтингу с первого дня.

Длинный вариант для постов и зеркал (в форму MakerWorld НЕ влезет):
«Tactile Map for the Blind — Europe, the Middle East and North Africa,
Braille Labels, Felt Terrain Relief, Snap-Together Puzzle (English + Serbian)»

## Summary (короткое описание, 498 символов — под лимит 500)

```
A 3D-printed tactile map for learning geography by touch: Europe east of Italy, the Balkans, Turkey, the Middle East, Arabia and North Africa - 27 countries labelled in braille. Raised borders that follow the terrain, 4 height plateaus (sea / lowland / plateau / mountains), a wavy sea, and an anchor ridge beside every number so an isolated braille cell is never ambiguous. Splits into 4 dovetail puzzle cards. Braille legends and alphabet cards in English AND Serbian. A gift for my blind friend.
```

## Description (основное поле)

```
I built this as a birthday gift for my blind friend, so he could learn geography with his fingers. It worked, so here are all the files, free.

WHAT THE MAP COVERS
The frame runs from 5°E to 70°E and from 12°N to 55°N: Europe east of Italy and Poland, the Balkans, Turkey, the Caucasus, the Middle East, the Arabian peninsula, North Africa from Algeria to Sudan, and Central Asia as far as Afghanistan. 27 countries carry a braille number. Western Europe, the British Isles and Scandinavia fall outside this frame — the generator is open source and the bounds are a single line of config, so a different region is a rebuild away.

WHAT THE FINGERS FEEL
• Country borders — a 1.2 mm ridge that rides on top of the local terrain, so you can trace a border continuously and still feel the relief on both sides of it
• Terrain — 4 tactile plateaus: sea / lowland / plateau / mountains (0 / 1 / 2 / 3 mm), banded at the real 500 m and 1500 m elevation lines, so all land sits at least 1 mm above the sea. At 0.2 mm layer height each step is exactly 5 layers
• Sea — wavy texture, impossible to confuse with land
• Country numbers — 27 countries carry a braille number at standard Marburg Medium spacing (rounded domes 1.6 mm across, 2.5 mm dot pitch, 6 mm cell pitch), placed at the most open point inside the country
• An anchor ridge beside every number — a raised bar the height of the braille cell. An isolated cell on a map has no line, no neighbouring cells and no baseline, so there is nothing to tell a reader WHICH of the six dot positions is raised. The ridge marks the left edge and the top and bottom rows, and the ambiguity disappears
• Legend cards — braille number to country name, plus touch samples of the sea, border and number-key textures
• Alphabet cards — every letter next to its braille cell, for learning braille (English 26 letters, Serbian Gajica 30 letters incl. Č Ć Dž Đ Lj Nj Š Ž)

THE PUZZLE
The 400 x 320 mm map splits into four 200 x 160 mm cards with dovetail tabs. Lay one card flat, lower its neighbour onto the tab from above — once assembled, the map cannot slide apart. Putting the puzzle together is itself a geography exercise.

PRINTING
• Material: PLA, any colour (it is read by touch, not by eye)
• Layer height: 0.2 mm — each terrain plateau is an exact multiple
• Infill: 15-20 %
• Supports: none, every part prints flat on the bed
• Each card is about 204 x 164 mm and fits any 220 x 220 bed
• Braille dots print as smooth domes — if your printer tends to blob, slow down the top layers

WHAT'S INCLUDED
4 puzzle cards (the map), braille legend EN, braille legend SR, braille alphabet card EN, braille alphabet card SR.
Every file is a verified watertight two-manifold — no repairs needed before slicing.

DESIGNED WITH, NOT JUST FOR
The map was tested by a blind reader and rebuilt on his feedback. The dots went from sharp cones at 1.5 mm spacing to standard rounded domes at 2.5 mm. The raised print digits became braille: he reads braille, not the shape of printed numerals. The anchor ridge was added because a lone braille cell in the middle of a country is genuinely ambiguous. The capital-city bumps were removed: they ate the space the number needed and were easy to mistake for a braille dot. The puzzle tabs became dovetails so the assembled map stops drifting apart.

3D relief maps have been shown to beat flat tactile graphics for comprehension and recall (Monash University Accessible Graphics group).

ABOUT THE PHOTOS
The photographs are of the first print. It carries raised Arabic numerals, the older sharper dots and straight tabs. The files in this download are the current version: braille number labels with an anchor ridge, 1.6 mm domed dots at 2.5 mm pitch, dovetail tabs and no capital-city bumps. The renders in the gallery show the current files. I would rather say that plainly than let you find it out at the printer.

CUSTOM MAPS / COMMISSIONS
The whole map is generated by open-source Python code (github.com/MAGLeb/worldbytouch, MIT). I take paid commissions for custom tactile maps — your country, your city, your school's region, braille in your language — and other educational tactile models for schools, museums and families.

The project lives at worldbytouch.com — the full story, the method, more photos, and the same pages in Serbian. Write to me at glebmaksimov@worldbytouch.com.

If you print this for a blind person or a school, please post a photo as a "make" — it genuinely helps the project reach the people who need it.
```

## Tags (через запятую в форму)

```
braille, tactile, blind, accessibility, low vision, assistive technology, map, tactile map, geography, europe, middle east, north africa, education, teaching aid, puzzle
```

## Category

`Geography` — именно она есть в списке площадки, её и выбирай.

## License на MakerWorld

Лицензия задаётся тремя вопросами. Для **CC BY** отвечай:

| Вопрос | Ответ |
|---|---|
| Allow adaptations of your work to be shared? | **Yes** |
| Allow commercial uses of your work? | **Yes** |
| Allow sharing **without attribution**? | **No** |

🔴 **Третий вопрос — ловушка, и раньше в этом файле он был записан неверно.**
Формулировка «Allow sharing without attribution?» инвертирована: «Yes» означает
«разрешаю не указывать авторство» и даёт **CC0** — public domain, любой может
перезалить карту как свою, без ссылки на тебя и на репозиторий. Три «Yes» подряд
дают именно CC0, а не CC BY. Чтобы получить CC BY, третий ответ — **No**.

CC0 сам по себе не катастрофа для accessibility-модели, но конкретно тут он
рвёт связку «модель → worldbytouch.com → заказы»: без обязательной атрибуции
реплики уедут без единой ссылки на тебя. Если сознательно хочешь public
domain — оставляй Yes, но это решение, а не дефолт.

(«Yes, as long as others share in the same way» на первом вопросе даст CC BY-SA
— тоже годится. Любой ответ «exclusively on MakerWorld» — не бери, это запирает
модель на площадке вопреки MIT-репозиторию.)

Рекомендую **CC BY** (или CC BY-SA) — remix-friendly, в духе MIT-репозитория и
важно для accessibility-аудитории. Дефолтный `Standard Digital File License`
не бери: он трактуется как no-derivatives, и тогда никто не сможет легально
добавить к модели свой print profile или доработку.

---

## Файлы (`data/output/makerworld/`, заливать в этом порядке)

| Файл | Что это |
|---|---|
| `Blind Map - 8 plates.3mf` | проект для открытия в слайсере: 8 плит, всё разложено и подписано. На MakerWorld — только в **raw**-слот, и то опционально |
| `Tactile Map - Card 1 of 4 - South-West (North Africa).stl` | нижний левый: Алжир, Тунис, Ливия, Египет, Судан |
| `Tactile Map - Card 2 of 4 - South-East (Arabia).stl` | нижний правый: Аравия, Йемен, Оман, юг Ирана |
| `Tactile Map - Card 3 of 4 - North-West (Europe).stl` | верхний левый: Европа, Балканы, Турция |
| `Tactile Map - Card 4 of 4 - North-East (Caucasus).stl` | верхний правый: Кавказ, Средняя Азия, Афганистан |
| `Braille Legend - English.stl` | легенда EN (номер → страна) |
| `Braille Legend - Serbian.stl` | легенда SR (номер → страна) |
| `Braille Alphabet Card - English.stl` | алфавит EN |
| `Braille Alphabet Card - Serbian.stl` | алфавит SR |

Цельную карту 400×320 (`tactile_map.stl`) НЕ заливай основным файлом — она не
влезает ни в один бытовой принтер. Если очень хочется — отдельным файлом в конце
с припиской "one-piece version, for large-format printers only".

## ⚠️ Главное про два слота загрузки

У MakerWorld **две разные формы**, и это источник ошибки
«The 3mf file is not generated by Bambu Studio…»:

| Слот | Что принимает | Проверка |
|---|---|---|
| **Print Profile** («Bambu Studio file») | ТОЛЬКО `.3mf`, сохранённый Bambu Studio через `Save Project As` | сервер **переслайсивает файл в облаке**; чужой 3mf отвергается |
| **Raw model files** | stl, obj, step, **любой 3mf**, zip и др. | без проверки провенанса |

Print Profile **не обязателен** — вики прямо помечает его «(Optional)»:
для публикации достаточно raw-файлов. Ошибка была из-за того, что 3mf попал
в первый слот вместо второго.

## Пошагово (без Bambu-принтера, ничего пересобирать не надо)

1. Открой <https://makerworld.com/en/my/models/publish>, тип — **Original**.
2. **Raw model files**: залей 8 STL из `data/output/makerworld/`.
   Именно STL, а не общий 3mf: у вики есть отдельный FAQ про то, что большие
   сводные 3mf (у нас 49 МБ геометрии в одном файле) виснут на 0 KB при загрузке.
   3mf можно добавить сверху как бонус — но в **raw**, не в Print Profile.
3. **Print Profile — пропусти.** Он помечен Optional.
4. Картинки: перетащи все 12 файлов из `data/output/makerworld_gallery/`,
   они уже пронумерованы в нужном порядке. `01_` поставь обложкой 4:3,
   `02_` — обложкой 3:4. Требование площадки «gallery images must include at
   least one clear photo of the actual printed object» закрыто восемью фото.
5. Вставь Title / Summary / Description / Tags из этого файла, выбери лицензию.
6. Publish.

## Пре-флайт: что сверить в заполненной форме перед Publish

Проверено по реальному черновику формы — три расхождения, все чинятся за минуту:

| Что | В форме было | Должно быть |
|---|---|---|
| Имена STL | `Europe Tactile Map - Puzzle Card N of 4` | залито из старого пакета. Удалить и перезалить 8 файлов из `data/output/makerworld/` — там `Tactile Map - Card N of 4 - South-West (North Africa)` и т.д. Имена видны посетителям, и старые снова обещают Европу |
| Третий вопрос лицензии | все три **Yes** → площадка показала **CC0** | третий — **No**, иначе это public domain без атрибуции |
| Теги | 11 штук, региона нет | добавить `europe`, `middle east`, `north africa`, `puzzle`, `teaching aid`. Лимит 50, места навалом. `learning` можно оставить |

Остальное в черновике верно: категория `Geography`, Model Name 50/50, Visibility
Public, все файлы с бейджем `Open Source` (то есть скачивание разрешено —
галочку не снимать), Laser & Cut — No, Exclusive Model Program — Not Eligible,
BOM не нужен. Картинок 10 из 16 плюс две обложки = ровно наши 12.

## Про Print Profile — позже и только честно

Профиль даёт вес в рейтинге (метрика = Downloads + **2×** Prints, а «print»
засчитывается только при печати через Bambu Handy/Studio из профиля). Но:

- Правила прямо запрещают «uploading print profiles without valid printed
  photos» — нужно фото объекта, напечатанного **именно этим профилем**.
  Текущие фото — с версии v1 (7-сегментные цифры, острые точки), так что
  профиль сейчас выкладывать нельзя.
- Если будешь делать: открыть в Bambu Studio → выбрать **стоковый** пресет
  Bambu Lab (например `Bambu Lab A1 0.4 nozzle` + `Bambu PLA Basic` +
  `0.20mm Standard`) → `File → Save Project As` (Ctrl+Shift+S).
  **Не** `Export plate sliced file` и **не** `Export G-code` — сгенерированный
  гкод-3mf отвергается отдельной ошибкой «is a sliced G-code file that does not
  contain the geometric data». Кастомные/изменённые пресеты тоже отвергаются.
- Облачный слайсинг ограничен 5 мин на плиту и 15 мин на файл — для плотной
  брайль-геометрии лучше делать профили по 1–2 плиты, а не один на восемь.
- Профиль может добавить **другой человек** с Bambu-принтером (кнопка
  «Add Print Profile» на странице модели), поставив галочку «Present the
  Points» — баллы уйдут тебе. Для бесплатной accessibility-модели это
  нормальная просьба.

**Exclusive Model Program не планируй**: вход — от 100 накопленных принтов,
плюс из программы исключены «plane/flat/2D models» и плоские карточки.

## Зеркала (сделать сразу, стоит ноль)

Printables и Thingiverse принимают голые STL без всякого профиля.
Для accessibility-модели это примерно удвоение охвата.

## Дальше

В первый комментарий под моделью: «Custom tactile maps of any region on
commission — contact me» со ссылкой на GitHub.

## Что ставить в галерею

Обязательное правило площадки: **хотя бы одно фото реальной печати**. Рендеры
допустимы как дополнение, если совпадают с объектом.

Всё уже сложено в **`data/output/makerworld_gallery/`** — 12 файлов,
пронумерованы в порядке загрузки. Открой папку и перетащи всё разом,
сортировка по имени = нужный порядок.

| # | Файл в папке | Что это |
|---|---|---|
| **01** | `01_cover_4x3_assembled_map.jpg` | **Cover 4:3** — собранная карта сверху, руки для масштаба |
| **02** | `02_cover_3x4_blind_reader.jpg` | **Cover 3:4** — незрячий читает карту; в приложении 3:4 крупнее |
| 03 | `03_all_six_printed_parts.jpg` | все 6 напечатанных штук разом — «что ты получишь» |
| 04 | `04_render_braille_macro.png` | **новые купольные точки и якорный гребень** — на фото их нет |
| 05 | `05_hands_assembling_relief.jpg` | руки ставят карточку: рельеф, штриховка моря, границы |
| 06 | `06_render_dovetail_joint.png` | **замок «ласточкин хвост»** — на фото его нет |
| 07 | `07_blind_reader_second_angle.jpg` | незрячий за картой, другой ракурс |
| 08 | `08_reading_card_and_legend.jpg` | карточка в руках, рядом легенда с брайлем |
| 09 | `09_card_in_hands_with_legend.jpg` | крупно: карточка и легенда |
| 10 | `10_full_map_top_down.jpg` | карта целиком сверху, второй ракурс |
| 11 | `11_render_all_files.png` | состав загрузки |
| 12 | `12_author_with_map.jpg` | автор с картой — лицо проекта |

Рендеры (04, 06, 11) идут рано специально: фото — с версии v1, а купола,
гребень и ласточкин хвост есть только в рендерах. Требование площадки
«хотя бы одно реальное фото печати» перевыполнено — реальных фото восемь.

Запас: `photo_6`, `photo_7` дублируют `07` по смыслу, `photo_12` — дубликат
`10`. Рендеры пересобираются `xvfb-run -a .venv/bin/python core/render_previews.py`
(нужен дисплей), папка галереи собирается руками.

Фото с лицами друга и автора — согласие есть, вопрос закрыт.

## Фото — от версии v1, и это уже написано в Description

Фото сняты со **старой** печати: печатные цифры, острые точки, прямые пазы.
Отдельную оговорку добавлять не надо — в Description уже стоит абзац
`ABOUT THE PHOTOS`, который проговаривает это прямым текстом.

Когда перепечатаешь v2 — переснять и убрать абзац. Фото это главный продающий
ассет, а заодно первый раз пощупаешь замок и гребень вживую.

## Чеклист съёмки v2

- [ ] Руки (в идеале — незрячего человека) читают карту — ГЛАВНОЕ фото
- [ ] Собранная карта целиком, вид сверху
- [ ] Макро брайль-точек (видно купола)
- [ ] Стык двух карточек: ласточкин хвост крупно
- [ ] Легенда + алфавитная карточка рядом с картой
- [ ] Видео 30 с: руки на карте, сборка пазла, чтение легенды
