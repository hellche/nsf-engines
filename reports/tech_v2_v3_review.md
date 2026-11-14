# Профиль технологии v2/v3: разбор по существу

2026-11-14. Что смотрели: топ-10 тем OpenAlex и топ-10 групп CPC по рейтингу (v2 — все предложения гранта,
v3 — научно-технические фрагменты; темы `max_bg`, CPC `centroid`), насколько они покрывают технологию гранта,
и пункты, которые всплыли в других расчётах (другие 3 способа оценки, другая версия, выбор v1), но в топ-10
не попали. Места ниже даны как «v2 / v3». Данные: `data/processed/tech_{v2,v3}_rank_*.csv.gz`.

**Версия 1 — не эталон.** Это прежний ручной выбор, обосновать его сейчас нельзя. Её темы и коды
используются только как ещё один источник кандидатов, которые стоит проверить глазами; «совпадение с v1»
не является мерой качества. Оценки «что должно было попасть» ниже — суждение по тексту гранта.

## Главный вывод

**Геометрия хорошо находит главную тему гранта, но топ-10 по одному числу покрывает обычно 1–2 из 3–5 тем.**
Ближайшая к гранту тема «заполняет» весь топ своими соседями, и вторая-третья темы гранта вытесняются:

| Engine | Топ-10 CPC целиком про | Что вытеснено (место v2 / v3) |
|---|---|---|
| Critical Mineral Accelerator | бурение скважин E21B (это нефть и газ) | извлечение металлов C22B 186/91, флотация B03D 49/77, геофизическая разведка G01V 34/78 |
| BRIDGES | сельхозтехника A01G/A01D/A01F | биоматериалы: C08H 955/545, C08L 57/136, целлюлоза D21C 276/376 |
| IMPACT (v2) | кресла и носилки для пациентов A61G | импланты A61F2 867/221, хирургия A61B17 919/283, лекарства A61K 90/252 |
| NEO-SMART (v2) | материалы инструментов и сплавы (B23B/B23C 2xxx, C22C) | полимеры C08J 3182/602, переработка пластика B29B17 1151/152, покрытия C09D 733/21 |
| Seafood (v3) | навигация судов B63B | переработка морепродуктов A23L17 1/23, A22C25 25/100 |

С темами OpenAlex то же самое в мягкой форме: у BRIDGES топ-10 — сельское хозяйство, а биопереработки нет
(«Biopolymer Synthesis» 66/78, «biodegradable polymer synthesis» 164/67, «Biofuel production» 674/55).

Значит, отбор топ-5 нельзя делать по одному общему рейтингу: нужен отбор **по каждой теме гранта отдельно**
(см. «Что исправить», п. 1).

## Почему геометрия ошибается: 6 механизмов

1. **Слово «Engine» = двигатель.** PatentSBERTa читает «engine» как мотор. В v2 топ-10 CPC у RuralSTAMINA — все
   F02B (двигатели внутреннего сгорания), у Quantum — F01B/F01K (паровые машины), у STELLAR — F01N/F02B
   (выхлоп, двигатели). Слово есть в самих аннотациях («NSF Engines award», «quantum technology engines»),
   а моя маскировка акронима на «the Engine» добавляет его ещё раз. В v3 фрагментах этого слова почти нет, поэтому
   v3 чище. **Это ошибка процедуры, исправляется.**
2. **Язык программы, а не технологии.** В v2 предложения про кадры, перевод исследований в практику, регион
   дают темы: «Translation Studies and Practices» (IMPACT #5 — от «Translation-to-Practice»; RETI 11-е),
   «Human Resource Development» (RETI #2), «Information Systems Education» (RETI #7), «Land Rights and Reforms» и
   «Border Security» (CMC #6, #9), «Maritime Ports and Logistics» (NEO-SMART #7 — от «Great Lakes shipping routes»),
   «Entrepreneurship Studies» (Quantum #10), «Public Administration» (Seafood #9–10). v3 это в основном убирает.
3. **Общие качества и отрасли-применения в фрагментах v3.** Промпт пропустил слова «resilience, reliability,
   efficiency» и списки отраслей. Отсюда у RETI v3 на 1-м месте «Regional resilience and development» и 3-е
   «Resilience and Mental Health»; у NEO-SMART v3 «Defense, Military, and Policy Studies» (из «aerospace,
   defense, …»); у BRIDGES v3 «Consumer Packaging Perceptions» (из «packaging sectors»); у Quantum v3 CPC
   G06Q20 «Payment architectures» и G06Q99 (из «finance and insurance»). **Промпт надо ужесточить (v3.1).**
4. **Многозначные слова.** «metallurgy» → «Metallurgy and Cultural Artifacts» (археология, CMC v3 #2);
   «mineral/geochemical» → «Archaeology and Rock Art», «Paleontology» (ACMA v3); «iron» → «Metalloenzymes and
   iron-sulfur proteins» (RETI v3 #5); «imaging» → «Dental Radiography», «Ocular Surface and Contact Lens»
   (IMPACT v2); «orthopedic» → «Veterinary Orthopedics» (IMPACT v3); «laser» + «vision care» → «Laser
   Applications in Dentistry», «Ophthalmology» (STELLAR); «harvest/processing» → «Processing poultry» A22C21
   (Seafood v2); «AI» → «Recognition of biometric patterns» G06V40 (Seafood v3); «quantum» → «Quantum-Dot
   Cellular Automata», «Quantum Gravity», «Education, Psychology, and Complexity Research» (Quantum).
5. **«Мусорные» пункты-всезнайки.** Темы с размытым описанием близки ко всему: «Diverse Industrial Engineering
   Technologies», «Engineering Applied Research», «Advanced Scientific Research Methods», «Diverse Topics in
   Contemporary Research» (FAST v3 #7), «Philosophy and Theoretical Science». В CPC — индексные группы серии 2000+
   с общими названиями («Materials of tools or workpieces composed of metals», B23B2222, B23C2224 — весь верх
   NEO-SMART и CMC) и группы «/99 Subject matter not provided for…» (A01J99, B21C99, G06Q99).
6. **Разный язык гранта и CPC.** Грант пишет рыночным языком, названия групп CPC — юридическим, и модель не
   видит связи: «hydrogen-based iron reduction» ↔ C21B13 «Making spongy iron or liquid steel, by direct processes»
   (RETI, 9014/3816); «AI-enabled Automatic Process Control» ↔ G05B19 «Programme-control systems» (FAST, 2385/1055);
   «digital twins» ↔ G05B17 «Systems involving the use of models or simulators» (BRIDGES, 7806/5798);
   «quantum sensing» ↔ G01R33 «Arrangements for measuring magnetic variables» (Quantum, 3222/975). В названии
   основной группы нужных слов нет — они есть в названиях её подгрупп.

Ещё одна находка: **два кода v1 устарели.** У FAST в v1 стоят H01L и H01L21 (процессы производства
полупроводников), а в схеме CPC 2026 их нет: они перенесены в новый подкласс H10P. Сам H10P геометрия
почти не находит (лучшая группа H10P36 «Gettering» на 123/72).

## По Engines

Оценка покрытия: **хорошо** — топ-10 описывает большую часть технологии гранта; **частично** — одну-две
темы из нескольких; **слабо** — главное не найдено или много шума.

| Engine | Темы OpenAlex | CPC | Лучше версия |
|---|---|---|---|
| BRIDGES | частично (только сельское хозяйство) | слабо (сельхозтехника, без биоматериалов) | v3 для тем |
| Critical Materials Crossroads | v2 слабо (шум), v3 частично (металлургия, процессы) | частично (C22B — извлечение металлов) | v3 для тем, v2 для CPC |
| Critical Mineral Accelerator | хорошо в v2 (дренаж шахт, извлечение, хвосты, биовыщелачивание) | слабо (бурение скважин) | v2 |
| FAST | хорошо (приборы, СБИС, SiC, GaN) | частично (приборы H10D; нет производства H10P и управления G05B) | v3 |
| Grid Modernization | хорошо в v2 (сети, трансформаторы, HVDC, безопасность) | частично (распределение H02J; нет трансформаторов H01F27, преобразователей H02M, атомного G21) | v2 |
| IMPACT | v2 слабо, v3 частично (опорно-двигательный аппарат, боль, инфекции) | v2 слабо (кресла для пациентов), v3 частично (медицинская ИТ G16H) | v3 |
| NEO-SMART | v2 частично (полимеры, металлы, порошковая металлургия), v3 слабо | частично (только металлы; в v3 появились покрытия C09D) | v2 для тем, v3 для CPC |
| Quantum Technologies | хорошо (вычисления, информация и криптография, оптика) | v2 слабо (паровые машины), v3 хорошо (G06N10, H04B10) | v3 |
| RETI | частично (энергосистемы, сталь в v2; шум про кадры и resilience) | частично (умные сети Y04S/Y02B, топливные элементы; нет восстановления железа и катализа) | v2 для тем |
| RuralSTAMINA | v2 слабо (бамбук, болезни сетчатки), v3 частично (биополимеры, микробные продукты) | v2 слабо (двигатели), v3 хорошо (биореакторы C12M, ферментация C12P на 15) | v3 |
| STELLAR | хорошо, но перекос в медицинские лазеры и офтальмологию | v2 слабо (выхлоп, двигатели), v3 хорошо (лазеры H01S) | v3 |
| Seafood | v3 хорошо (рыболовство и аквакультура, моллюски, океанография) | v2 — переработка рыбы, v3 — навигация судов: каждая покрывает половину | вместе |

### Что должно было попасть, но геометрия не выбрала

| Engine | Пункт (место v2 / v3) | Почему не выбран |
|---|---|---|
| BRIDGES | Biopolymer Synthesis 66/78; biodegradable polymers 164/67; Biofuel production 674/55; C08H 955/545; D21C 276/376 | вытеснено сельским хозяйством (мех. 1 в выводе); в гранте «biobased products» без слов «lignin, cellulose, polymer» |
| BRIDGES | G05B17 (модели, цифровые двойники) 7806/5798 | разный язык (мех. 6) |
| CMC | B01J19 (химические процессы, непрерывный поток) 1255/2113; G05B13 (адаптивное управление) 7439/7625 | разный язык; «continuous flow processing» не похоже на названия групп |
| ACMA | C22B 186/91; B03D (флотация) 49/77; G01V (разведка) 34/78 | вытеснено бурением E21B; «mineral» близко к «drilling for minerals» |
| FAST | H10P (производство полупроводников); G05B19 (программное управление) 2385/1055 | устаревший код v1; разный язык |
| Grid | H01F27 (трансформаторы) 2477/628; H02M5 (преобразователи) 934/99; G21C/G21D (атомные реакторы) 514/942, 49/313; H04L63 (сетевая безопасность) 266/255 | вытеснено распределением H02J; «nuclear construction» — одна фраза |
| IMPACT | Bone health and osteoporosis 153/15; Osteoarthritis 497/20; Rheumatoid Arthritis 480/11; A61F2 (импланты) 867/221; A61B17 (хирургия) 919/283 | грант говорит «MSK conditions» общими словами; v3 уже ближе |
| NEO-SMART | Synthesis and properties of polymers 26/98; Machine Learning in Materials Science 13/28; Additive Manufacturing 53/13; C08J 3182/602; B29B17 1151/152 | металлы доминируют; индексные коды 2xxx в верху (мех. 5) |
| Quantum | Cold Atom Physics 42/21; Superconducting and THz Devices 46/31; G01R33 (магнитометрия) 3222/975 | квантовые сенсоры в CPC без слова «quantum» (мех. 6) |
| RETI | Advancements in Solid Oxide Fuel Cells 455/93; C21B13 (прямое восстановление железа) 9014/3816; B01J (катализ) 568/2791; H01M10 (аккумуляторы) 64/151 | вытеснено энергосистемами; разный язык |
| RuralSTAMINA | Enzyme Production 1451/12; Catalysis for Biomass Conversion 23/13 | в v2 шум; в v3 рядом с топ-10 |
| STELLAR | Laser Material Processing 13/18; Advanced optical system design 59/43; G02B (оптические элементы) 232/11; B23K26 (лазерная обработка) 817/239 | перекос в медицинские лазеры («vision care»); производство оптики — слабая фраза в гранте |
| Seafood | Water Quality Monitoring 11/140; Food Industry and Aquatic Biology 31/52; A22C25 (переработка рыбы) 25/100 | v3 ушёл в «ocean intelligence» → навигация |

## Что исправить (по убыванию пользы)

1. **Отбор по темам гранта, а не по одному рейтингу.** В v3 у каждого фрагмента своя близость ко всем пунктам:
   брать лучшие пункты **для каждого фрагмента** (или группы фрагментов) по очереди, с запретом почти-дубликатов
   (MMR, maximal marginal relevance). Тогда у ACMA в топ попадут и бурение, и извлечение C22B, и разведка G01V.
2. **Убрать слово «Engine(s)»** (когда речь о программе NSF) и не подставлять «the Engine» при маскировке —
   заменять на нейтральное «the program» или удалять.
3. **Промпт v3.1:** не извлекать отрасли-применения («automotive, packaging», «aerospace, defense»,
   «pharmaceuticals, finance and insurance») и общие качества («resilience, reliability, efficiency») без
   технического объекта.
4. **Текст группы CPC = название группы + названия её подгрупп** (хотя бы первого уровня). Это даст нужные слова:
   «hydrogen», «direct reduction», «magnetometer», «flotation». Индексные группы 2000+ и «/99» либо исключить,
   либо понизить.
5. **Обновить коды v1** под схему CPC 2026 (H01L21 → H10P).
6. Шаг LLM на топ-50 уберёт шум (мех. 2–5), но **не добавит пропущенные темы** — поэтому п. 1 важнее LLM.
