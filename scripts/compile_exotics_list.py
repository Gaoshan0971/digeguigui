#!/usr/bin/env python3
"""
异宠全量名录：根据领域知识编制的宠物蛇/蜥蜴/守宫/蛙完整名单
跳过已有35种，目标新增~150种，基因库冲击550+
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# 宠物蛇：游蛇科+蟒科+蚺科+闪鳞蛇科
SNAKES_PET = [
    # === 游蛇科 Colubridae (宠物蛇主力) ===
    # 王蛇属 Lampropeltis
    ("墨西哥黑王蛇", "Lampropeltis getula nigrita"),
    ("佛州王蛇", "Lampropeltis getula floridana"),
    ("阿帕拉契王蛇", "Lampropeltis getula meansi"),
    ("沙漠王蛇", "Lampropeltis splendida"),
    ("圣路易斯波托西王蛇", "Lampropeltis mexicana"),
    ("格雷格王蛇", "Lampropeltis greeri"),
    ("亚利桑那山王蛇", "Lampropeltis pyromelana"),
    ("加州山王蛇", "Lampropeltis zonata"),
    ("纳尔逊奶蛇", "Lampropeltis nelsoni"),
    ("洪都拉斯奶蛇", "Lampropeltis hondurensis"),
    ("普埃布拉奶蛇", "Lampropeltis campbelli"),
    ("西纳洛亚奶蛇", "Lampropeltis sinaloae"),
    ("红王蛇", "Lampropeltis elapsoides"),
    
    # 鼠蛇属 Pantherophis
    ("白条鼠蛇", "Pantherophis alleghaniensis"),
    ("贝氏鼠蛇", "Pantherophis bairdi"),
    ("黄鼠蛇", "Pantherophis vulpinus"),
    ("东黑鼠蛇", "Pantherophis spiloides"),
    ("灰鼠蛇", "Pantherophis emoryi"),
    
    # 其他游蛇
    ("牛蛇", "Pituophis catenifer"),
    ("松蛇", "Pituophis melanoleucus"),
    ("佛州松蛇", "Pituophis ruthveni"),
    ("东方靛青蛇", "Drymarchon couperi"),
    ("德州靛青蛇", "Drymarchon melanurus"),
    ("中国王锦蛇", "Elaphe carinata"),
    ("棕黑锦蛇", "Elaphe schrenckii"),
    ("日本鼠蛇", "Elaphe climacophora"),
    ("俄罗斯鼠蛇", "Elaphe dione"),
    ("四线锦蛇", "Elaphe quatuorlineata"),
    ("美女蛇", "Elaphe taeniura"),
    ("黑眉锦蛇", "Orthriophis taeniurus"),
    ("犀牛鼠蛇", "Gonyosoma boulengeri"),
    ("绿鼠蛇", "Gonyosoma oxycephalum"),
    ("红尾绿鼠蛇", "Gonyosoma jansenii"),
    ("蓝美容蛇", "Gonyosoma coeruleum"),
    ("马达加斯加猫眼蛇", "Madagascarophis colubrinus"),
    ("非洲食卵蛇", "Dasypeltis scabra"),
    
    # === 蟒科 Pythonidae ===
    ("地毯蟒", "Morelia spilota"),
    ("丛林地毯蟒", "Morelia spilota cheynei"),
    ("钻石蟒", "Morelia spilota spilota"),
    ("绿树蟒", "Morelia viridis"),
    ("粗鳞蟒", "Morelia carinata"),
    ("童蟒", "Antaresia childreni"),
    ("斑童蟒", "Antaresia stimsoni"),
    ("点童蟒", "Antaresia maculosa"),
    ("珀兹星蟒", "Antaresia perthensis"),
    ("黑头蟒", "Aspidites melanocephalus"),
    ("沃玛蟒", "Aspidites ramsayi"),
    ("安哥拉蟒", "Python anchietae"),
    ("血蟒", "Python brongersmai"),
    ("婆罗洲短尾蟒", "Python breitensteini"),
    ("苏门答腊短尾蟒", "Python curtus"),
    ("缅甸蟒", "Python bivittatus"),
    ("印度蟒", "Python molurus"),
    ("网纹蟒", "Malayopython reticulatus"),
    ("非洲岩蟒", "Python sebae"),
    
    # === 蚺科 Boidae ===
    ("红尾蚺", "Boa constrictor"),
    ("哥伦比亚红尾蚺", "Boa imperator"),
    ("阿根廷彩虹蚺", "Epicrates alvarezi"),
    ("巴西彩虹蚺", "Epicrates cenchria"),
    ("哥伦比亚彩虹蚺", "Epicrates maurus"),
    ("古巴地蚺", "Chilabothrus angulifer"),
    ("肯尼亚沙蚺", "Eryx colubrinus"),
    ("印度沙蚺", "Eryx johnii"),
    ("粗鳞沙蚺", "Eryx conicus"),
    ("橡胶蚺", "Charina bottae"),
    ("翡翠树蚺", "Corallus caninus"),
    ("亚马逊树蚺", "Corallus hortulanus"),
    
    # === 林蚺科 Tropidophiidae ===
    ("古巴林蚺", "Tropidophis melanurus"),
]

# 蜥蜴类
LIZARDS_PET = [
    # === 飞蜥科 Agamidae ===
    ("东部鬃狮蜥", "Pogona barbata"),
    ("侏儒鬃狮蜥", "Pogona henrylawsoni"),
    ("小鬃狮蜥", "Pogona minor"),
    ("澳洲水龙", "Intellagama lesueurii"),
    ("菲律宾斑帆蜥", "Hydrosaurus pustulatus"),
    ("苏拉威西斑帆蜥", "Hydrosaurus celebensis"),
    ("斗篷蜥", "Chlamydosaurus kingii"),
    ("刺尾飞蜥", "Uromastyx acanthinura"),
    ("埃及刺尾飞蜥", "Uromastyx aegyptia"),
    ("华丽刺尾飞蜥", "Uromastyx ornata"),
    ("马里刺尾飞蜥", "Uromastyx geyri"),
    ("印度刺尾飞蜥", "Uromastyx hardwickii"),
    ("蝴蝶蜥", "Leiolepis belliana"),
    
    # === 美洲鬣蜥科 Iguanidae ===
    ("犀牛鬣蜥", "Cyclura cornuta"),
    ("古巴鬣蜥", "Cyclura nubila"),
    ("蓝岩鬣蜥", "Cyclura lewisi"),
    ("斐济冠鬣蜥", "Brachylophus vitiensis"),
    ("斐济带鬣蜥", "Brachylophus fasciatus"),
    ("墨西哥刺尾鬣蜥", "Ctenosaura pectinata"),
    ("黑刺尾鬣蜥", "Ctenosaura similis"),
    ("海鬣蜥", "Amblyrhynchus cristatus"),
    
    # === 变色龙科 Chamaeleonidae ===
    ("高冠变色龙", "Chamaeleo calyptratus"),
    ("七彩变色龙", "Furcifer pardalis"),
    ("杰克逊变色龙", "Trioceros jacksonii"),
    ("盔甲变色龙", "Trioceros hoehnelii"),
    ("四角变色龙", "Trioceros quadricornis"),
    ("地毯变色龙", "Furcifer lateralis"),
    ("侏儒变色龙", "Rhampholeon spectrum"),
    ("奥力士变色龙", "Furcifer oustaleti"),
    
    # === 巨蜥科 Varanidae ===
    ("砂巨蜥", "Varanus gouldii"),
    ("刺尾巨蜥", "Varanus acanthurus"),
    ("翠绿树巨蜥", "Varanus prasinus"),
    ("黑树巨蜥", "Varanus beccarii"),
    ("蓝树巨蜥", "Varanus macraei"),
    ("金伯利岩巨蜥", "Varanus glauerti"),
    ("芒果巨蜥", "Varanus indicus"),
    ("科莫多巨蜥", "Varanus komodoensis"),
    ("萨氏巨蜥", "Varanus salvadorii"),
    
    # === 石龙子科 Scincidae ===
    ("松果蜥", "Tiliqua rugosa"),
    ("中部蓝舌", "Tiliqua multifasciata"),
    ("西部蓝舌", "Tiliqua occipitalis"),
    ("火焰石龙子", "Lepidothyris fernandi"),
    ("猴尾石龙子", "Corucia zebrata"),
    ("红眼鳄鱼石龙子", "Tribolonotus gracilis"),
    ("斯奈德石龙子", "Scincus scincus"),
    
    # === 其余蜥蜴 ===
    ("红尾鞭尾蜥", "Ameiva ameiva"),
    ("绿鞭尾蜥", "Ameiva ameiva"),
    ("犰狳蜥", "Ouroborus cataphractus"),
    ("巨型环颈蜥", "Crotaphytus bicinctores"),
    ("豹纹蜥", "Gambelia wislizenii"),
    ("金泰加", "Tupinambis teguixin"),
]

# 守宫类
GECKOS_PET = [
    # === 睑虎科 Eublepharidae ===
    ("西部豹纹守宫", "Eublepharis macularius"),  # 已有
    ("海南睑虎", "Goniurosaurus hainanensis"),
    ("广西睑虎", "Goniurosaurus lichtenfelderi"),
    ("越南睑虎", "Goniurosaurus araneus"),
    ("琉球睑虎", "Goniurosaurus kuroiwae"),
    ("爪哇睑虎", "Goniurosaurus orientalis"),
    
    # === 澳虎科 Diplodactylidae ===
    ("盖勾亚守宫", "Rhacodactylus auriculatus"),
    ("萨拉辛守宫", "Rhacodactylus sarasinorum"),
    ("特里基守宫", "Rhacodactylus trachyrhynchus"),
    ("莫斯岛石龙子守宫", "Naultinus elegans"),
    
    # === 壁虎科 Gekkonidae ===
    ("头盔守宫", "Geckolepis maculata"),
    ("豹纹睑虎", "Aeluroscalabotes felinus"),
    ("金黄日行守宫", "Phelsuma laticauda"),
    ("马岛日行守宫", "Phelsuma madagascariensis"),
    ("林氏日行守宫", "Phelsuma lineata"),
    ("蓝尾日行守宫", "Phelsuma klemmeri"),
    ("蛙眼守宫", "Teratoscincus scincus"),
    ("裸趾守宫", "Lygodactylus williamsi"),
    ("头盔守宫", "Tarentola mauritanica"),
    ("大守宫/蛤蚧", "Gekko gecko"),
    ("豹守宫", "Paroedura picta"),
    
    # === 鳞脚蜥科 Pygopodidae ===
    ("鳞脚蜥", "Lialis burtonis"),
]

# 蛙类
FROGS_PET = [
    # === 角花蟾科 Ceratophryidae ===
    ("巴西角蛙", "Ceratophrys aurita"),
    ("哥伦比亚角蛙", "Ceratophrys calcarata"),
    ("草原角蛙", "Ceratophrys stolzmanni"),
    ("钟角蛙", "Ceratophrys ornata"),
    ("霸王角蛙", "Ceratophrys cornuta"),
    
    # === 箭毒蛙科 Dendrobatidae ===
    ("钴蓝箭毒蛙", "Dendrobates tinctorius"),
    ("金色箭毒蛙", "Phyllobates terribilis"),
    ("绿黑箭毒蛙", "Dendrobates auratus"),
    ("迷彩箭毒蛙", "Dendrobates leucomelas"),
    ("草莓箭毒蛙", "Oophaga pumilio"),
    ("三色箭毒蛙", "Epipedobates tricolor"),
    
    # === 雨蛙科 Hylidae ===
    ("灰树蛙", "Hyla versicolor"),
    ("绿树蛙", "Hyla cinerea"),
    ("松鼠树蛙", "Hyla squirella"),
    ("白唇树蛙", "Boana albomarginata"),
    ("巨人树蛙", "Nyctimystes infrafrenatus"),
    
    # === 姬蛙科 Microhylidae ===
    ("小丑蛙", "Chiasmocleis ventrimaculata"),
    ("大理石草蛙", "Phrynomantis bifasciatus"),
    
    # === 蟾蜍科 Bufonidae (宠物种) ===
    ("中华大蟾蜍", "Bufo gargarizans"),
    ("科罗拉多河蟾", "Incilius alvarius"),
    ("红腹铃蟾", "Bombina orientalis"),
    
    # === 细趾蟾科 Leptodactylidae ===
    ("草原蛙", "Leptodactylus fuscus"),
]

# ===== 合并 + 去重 =====
ALL_NEW = []
EXISTING = set()  # already in DB from first 35

# Mark existing 35 by latin name
import subprocess, json
try:
    r = subprocess.run(['sqlite3', '/home/ubuntu/digeguigui/data/digeguigui.db',
        "SELECT DISTINCT lower(name_latin) FROM species WHERE category IN ('蛇','蜥蜴','蛙','守宫')"],
        capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        if line:
            EXISTING.add(line.strip())
except:
    pass

def add_list(lst):
    for cn, lat in lst:
        key = lat.lower().strip()
        if key in EXISTING:
            continue
        ALL_NEW.append((cn, lat))
        EXISTING.add(key)

add_list(SNAKES_PET)
add_list(LIZARDS_PET)
add_list(GECKOS_PET)
add_list(FROGS_PET)

print(f"📋 异宠候选: {len(SNAKES_PET)+len(LIZARDS_PET)+len(GECKOS_PET)+len(FROGS_PET)} 种")
print(f"📋 新增(去重): {len(ALL_NEW)} 种")
print(f"  🐍 蛇: {sum(1 for x in ALL_NEW if x in [(c,l) for c,l in SNAKES_PET])}")
print(f"  🦎 蜥蜴: {sum(1 for x in ALL_NEW if x in [(c,l) for c,l in LIZARDS_PET])}")
print(f"  🦎 守宫: {sum(1 for x in ALL_NEW if x in [(c,l) for c,l in GECKOS_PET])}")
print(f"  🐸 蛙: {sum(1 for x in ALL_NEW if x in [(c,l) for c,l in FROGS_PET])}")

# Save list
outpath = '/home/ubuntu/digeguigui/data/exotics_candidates.json'
with open(outpath, 'w') as f:
    json.dump([{"name_cn":c, "name_latin":l} for c,l in ALL_NEW], f, ensure_ascii=False, indent=2)
print(f"\n💾 候选名单: {outpath}")
