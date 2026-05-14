#!/usr/bin/env python3
"""
scrape_exotics_full.py — 异宠基因库全量扩展（蛇/蜥蜴/蛙/守宫）
三源爬取：GBIF + iNaturalist + ReptileDB
目标：~230 新品种 → 基因库总数 500+

用法: /usr/bin/python3 scripts/scrape_exotics_full.py
输出: data/species_exotics_full.json
"""
import sys, os, json

# 动态加载 scrape_species_v3.py 核心函数
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "scrape_v3",
    os.path.join(os.path.dirname(__file__), "scrape_species_v3.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# 覆盖输出文件和品种列表
mod.OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "species_exotics_full.json"
)
mod.DELAY = 1.5  # 略微加快

mod.SPECIES = [
    # ========================================================
    # 🐍 蛇类 (Serpentes) — 目标 70+ 种
    # ========================================================
    # --- Colubridae: 游蛇科 (rat snakes, king snakes, milk snakes, hognose, garter, etc.) ---
    ("东部鼠蛇", "Pantherophis alleghaniensis"),
    ("中部鼠蛇", "Pantherophis spiloides"),
    ("贝氏鼠蛇", "Pantherophis bairdi"),
    ("大平原鼠蛇", "Pantherophis emoryi"),
    ("狐鼠蛇", "Pantherophis vulpinus"),
    ("墨西哥王蛇", "Lampropeltis mexicana"),
    ("亚利桑那山王蛇", "Lampropeltis pyromelana"),
    ("加州山王蛇", "Lampropeltis zonata"),
    ("鲁氏王蛇", "Lampropeltis ruthveni"),
    ("斑点王蛇", "Lampropeltis holbrooki"),
    ("沙漠王蛇", "Lampropeltis splendida"),
    ("草原王蛇", "Lampropeltis calligaster"),
    ("中美洲奶蛇", "Lampropeltis abnorma"),
    ("大西洋奶蛇", "Lampropeltis polyzona"),
    ("巴拿马奶蛇", "Lampropeltis micropholis"),
    ("猩红王蛇", "Lampropeltis elapsoides"),
    ("墨西哥奶蛇", "Lampropeltis annulata"),
    ("平原奶蛇", "Lampropeltis gentilis"),
    ("墨西哥猪鼻蛇", "Heterodon kennerlyi"),
    ("南部猪鼻蛇", "Heterodon simus"),
    ("牛蛇", "Pituophis catenifer"),
    ("松蛇", "Pituophis melanoleucus"),
    ("路易斯安那松蛇", "Pituophis ruthveni"),
    ("东部靛蓝蛇", "Drymarchon couperi"),
    ("黑尾靛蓝蛇", "Drymarchon melanurus"),
    ("王锦蛇", "Elaphe carinata"),
    ("黑眉锦蛇", "Elaphe taeniura"),
    ("日本锦蛇", "Elaphe climacophora"),
    ("阿穆尔锦蛇", "Elaphe schrenckii"),
    ("迪奥纳锦蛇", "Elaphe dione"),
    ("红尾绿鼠蛇", "Gonyosoma oxycephalum"),
    ("犀牛鼠蛇", "Gonyosoma boulengeri"),
    ("虎鼠蛇", "Spilotes pullatus"),
    ("辐射鼠蛇", "Coelognathus radiatus"),
    ("金环猫蛇", "Boiga dendrophila"),
    ("普通带蛇", "Thamnophis sirtalis"),
    ("方格带蛇", "Thamnophis marcianus"),
    ("西部陆栖带蛇", "Thamnophis elegans"),
    ("宽带水蛇", "Nerodia fasciata"),
    ("北方水蛇", "Nerodia sipedon"),
    ("加州鞭蛇", "Masticophis lateralis"),
    ("东部猪鼻蛇", "Heterodon platirhinos"),
    # --- Pythonidae: 蟒科 ---
    ("缅甸蟒", "Python bivittatus"),
    ("血蟒", "Python curtus"),
    ("红血蟒", "Python brongersmai"),
    ("婆罗洲血蟒", "Python breitensteini"),
    ("地毯蟒", "Morelia spilota"),
    ("绿树蟒", "Morelia viridis"),
    ("布氏蟒", "Morelia bredli"),
    ("粗鳞蟒", "Morelia carinata"),
    ("童蟒", "Antaresia childreni"),
    ("斯氏点蟒", "Antaresia stimsoni"),
    ("斑点蟒", "Antaresia maculosa"),
    ("侏儒蟒", "Antaresia perthensis"),
    ("马氏蟒", "Liasis mackloti"),
    ("橄榄蟒", "Liasis olivaceus"),
    ("旺氏蟒", "Aspidites ramsayi"),
    ("黑头蟒", "Aspidites melanocephalus"),
    ("网纹蟒", "Malayopython reticulatus"),
    ("紫晶蟒", "Simalia amethistina"),
    # --- Boidae: 蚺科 ---
    ("红尾蚺", "Boa constrictor"),
    ("中美蚺", "Boa imperator"),
    ("翡翠树蚺", "Corallus caninus"),
    ("亚马逊树蚺", "Corallus hortulanus"),
    ("巴西彩虹蚺", "Epicrates cenchria"),
    ("哥伦比亚彩虹蚺", "Epicrates maurus"),
    ("古巴蚺", "Chilabothrus angulifer"),
    ("肯尼亚沙蚺", "Eryx colubrinus"),
    ("粗鳞沙蚺", "Eryx conicus"),
    ("印度沙蚺", "Eryx johnii"),
    ("太平洋地蚺", "Candoia carinata"),
    ("杜氏蚺", "Acrantophis dumerili"),
    ("马达加斯加树蚺", "Sanzinia madagascariensis"),
    # --- Elapidae: 眼镜蛇科 (pet-grade) ---
    ("德克萨斯珊瑚蛇", "Micrurus tener"),
    # --- Viperidae: 蝰科 (pet-grade) ---
    ("加蓬咝蝰", "Bitis gabonica"),
    ("鼓腹咝蝰", "Bitis arietans"),
    ("铜头蝮", "Agkistrodon contortrix"),
    ("棉口蝮", "Agkistrodon piscivorus"),

    # ========================================================
    # 🦎 守宫 (Gekkota) — 目标 30+ 种
    # ========================================================
    # --- Eublepharidae: 睑虎科 ---
    ("印度豹纹守宫", "Eublepharis hardwickii"),
    ("伊朗豹纹守宫", "Eublepharis angramainyu"),
    ("土库曼豹纹守宫", "Eublepharis turcmenicus"),
    ("李氏洞穴守宫", "Goniurosaurus lichtenfelderi"),
    ("卢氏洞穴守宫", "Goniurosaurus luii"),
    ("蛛网洞穴守宫", "Goniurosaurus araneus"),
    ("霸王岭洞穴守宫", "Goniurosaurus bawanglingensis"),
    ("东方洞穴守宫", "Goniurosaurus orientalis"),
    ("西部带纹守宫", "Coleonyx variegatus"),
    ("中美带纹守宫", "Coleonyx mitratus"),
    ("优雅带纹守宫", "Coleonyx elegans"),
    ("非洲爪守宫", "Holodactylus africanus"),
    # --- Diplodactylidae: 外爪守宫科 ---
    ("粗吻巨人守宫", "Rhacodactylus trachyrhynchus"),
    ("萨氏巨人守宫", "Rhacodactylus sarasinorum"),
    ("魔物守宫", "Mniarogekko chahoua"),
    ("萨拉辛守宫", "Correlophus sarasinorum"),
    ("维氏守宫", "Eurydactylodes vieillardi"),
    ("巴伐亚守宫", "Bavayia cyclura"),
    # --- Gekkonidae: 壁虎科 ---
    ("马达加斯加日行守宫", "Phelsuma madagascariensis"),
    ("金粉日行守宫", "Phelsuma laticauda"),
    ("条纹日行守宫", "Phelsuma lineata"),
    ("克莱默日行守宫", "Phelsuma klemmeri"),
    ("四眼日行守宫", "Phelsuma quadriocellata"),
    ("橄榄日行守宫", "Phelsuma dubia"),
    ("大壁虎", "Gekko gecko"),
    ("特纳厚趾守宫", "Chondrodactylus turneri"),
    ("疣尾蜥虎", "Hemidactylus frenatus"),
    # --- Sphaerodactylidae ---
    ("刚果厚尾守宫", "Hemitheconyx taylori"),
    # --- Pygopodidae ---
    ("伯氏鳞脚蜥", "Lialis burtonis"),
    # --- Carphodactylidae ---
    ("脊尾守宫", "Nephrurus levis"),
    ("棘尾脊尾守宫", "Nephrurus asper"),
    ("星点脊尾守宫", "Nephrurus stellatus"),

    # ========================================================
    # 🦎 蜥蜴 (Sauria/Lacertilia) — 目标 60+ 种
    # ========================================================
    # --- Agamidae: 飞蜥科 ---
    ("东部鬃狮蜥", "Pogona barbata"),
    ("侏儒鬃狮蜥", "Pogona minor"),
    ("兰氏鬃狮蜥", "Pogona henrylawsoni"),
    ("纳拉伯鬃狮蜥", "Pogona nullarbor"),
    ("澳洲水龙", "Physignathus lesueurii"),
    ("菲律宾帆蜥", "Hydrosaurus pustulatus"),
    ("印尼帆蜥", "Hydrosaurus amboinensis"),
    ("东部水龙", "Intellagama lesueurii"),
    ("埃及刺尾蜥", "Uromastyx aegyptia"),
    ("华丽刺尾蜥", "Uromastyx ornata"),
    ("北非刺尾蜥", "Uromastyx acanthinura"),
    ("盖氏刺尾蜥", "Uromastyx geyri"),
    ("沙漠刺尾蜥", "Uromastyx dispar"),
    ("伞蜥", "Chlamydosaurus kingii"),
    ("蝴蝶蜥", "Leiolepis belliana"),
    # --- Iguanidae: 美洲鬣蜥科 ---
    ("小安的列斯鬣蜥", "Iguana delicatissima"),
    ("黑刺尾鬣蜥", "Ctenosaura similis"),
    ("墨西哥刺尾鬣蜥", "Ctenosaura pectinata"),
    ("五棱刺尾鬣蜥", "Ctenosaura quinquecarinata"),
    ("犀牛鬣蜥", "Cyclura cornuta"),
    ("古巴鬣蜥", "Cyclura nubila"),
    ("普通叩壁蜥", "Sauromalus ater"),
    ("沙漠鬣蜥", "Dipsosaurus dorsalis"),
    # --- Varanidae: 巨蜥科 ---
    ("棘尾巨蜥", "Varanus acanthurus"),
    ("黑头巨蜥", "Varanus tristis"),
    ("绿树巨蜥", "Varanus prasinus"),
    ("帝汶巨蜥", "Varanus timorensis"),
    ("水巨蜥", "Varanus salvator"),
    ("草原巨蜥", "Varanus exanthematicus"),
    ("尼罗巨蜥", "Varanus niloticus"),
    ("蓝树巨蜥", "Varanus macraei"),
    ("金头巨蜥", "Varanus melinus"),
    # --- Chamaeleonidae: 变色龙科 ---
    ("高冠变色龙", "Chamaeleo calyptratus"),
    ("七彩变色龙", "Furcifer pardalis"),
    ("毯纹变色龙", "Furcifer lateralis"),
    ("杰克森变色龙", "Trioceros jacksonii"),
    ("赫氏变色龙", "Trioceros hoehnelii"),
    ("侏儒枯叶变色龙", "Rhampholeon spectrum"),
    ("角头变色龙", "Chamaeleo dilepis"),
    ("南非侏儒变色龙", "Bradypodion pumilum"),
    # --- Scincidae: 石龙子科 ---
    ("松果蜥", "Tiliqua rugosa"),
    ("西部蓝舌蜥", "Tiliqua occipitalis"),
    ("中部蓝舌蜥", "Tiliqua multifasciata"),
    ("斑点蓝舌蜥", "Tiliqua nigrolutea"),
    ("所罗门猴尾蜥", "Corucia zebrata"),
    ("红眼鳄蜥", "Tribolonotus gracilis"),
    # --- Teiidae: 鞭尾蜥科 ---
    ("金泰加蜥", "Salvator duseni"),
    ("哥伦比亚泰加", "Tupinambis teguixin"),
    ("凯门蜥", "Dracaena guianensis"),
    # --- Gerrhosauridae: 盾甲蜥科 ---
    ("黄喉盾甲蜥", "Gerrhosaurus flavigularis"),
    ("巨型盾甲蜥", "Gerrhosaurus validus"),
    # --- Crotaphytidae: 环颈蜥科 ---
    ("长鼻豹蜥", "Gambelia wislizenii"),
    # --- Dactyloidae: 安乐蜥科 ---
    ("骑士安乐蜥", "Anolis equestris"),
    ("棕安乐蜥", "Anolis sagrei"),
    ("阿利森安乐蜥", "Anolis allisoni"),
    # --- Corytophanidae: 冠蜥科 ---
    ("绿双冠蜥", "Basiliscus plumifrons"),
    ("棕双冠蜥", "Basiliscus vittatus"),
    # --- Cordylidae: 绳蜥科 ---
    ("巨型绳蜥", "Smaug giganteus"),
    ("莫桑比克绳蜥", "Cordylus tropidosternum"),
    # --- Lacertidae: 正蜥科 ---
    ("珠宝蜥", "Timon lepidus"),
    ("绿蜥", "Lacerta viridis"),
    # --- Other popular pet lizards ---
    ("德州角蜥", "Phrynosoma cornutum"),
    ("带斑蜥", "Aspidoscelis tigris"),
    ("查尔斯岛熔岩蜥", "Microlophus albemarlensis"),

    # ========================================================
    # 🐸 蛙类 (Anura) — 目标 55+ 种
    # ========================================================
    # --- Hylidae: 雨蛙科 ---
    ("美洲绿树蛙", "Hyla cinerea"),
    ("灰树蛙", "Hyla versicolor"),
    ("欧洲树蛙", "Hyla arborea"),
    ("白唇树蛙", "Litoria infrafrenata"),
    ("华丽雨蛙", "Litoria splendida"),
    ("红眼绿树蛙", "Litoria chloris"),
    ("金铃蛙", "Litoria aurea"),
    ("莫尔树蛙", "Litoria moorei"),
    ("古巴树蛙", "Osteopilus septentrionalis"),
    ("面具树蛙", "Smilisca phaeota"),
    ("鸭嘴树蛙", "Triprion petasatus"),
    # --- Dendrobatidae: 箭毒蛙科 ---
    ("染色箭毒蛙", "Dendrobates tinctorius"),
    ("绿黑箭毒蛙", "Dendrobates auratus"),
    ("黄带箭毒蛙", "Dendrobates leucomelas"),
    ("黄纹箭毒蛙", "Dendrobates truncatus"),
    ("金色箭毒蛙", "Phyllobates terribilis"),
    ("双色箭毒蛙", "Phyllobates bicolor"),
    ("条纹箭毒蛙", "Phyllobates vittatus"),
    ("安氏箭毒蛙", "Epipedobates anthonyi"),
    ("拟箭毒蛙", "Ranitomeya imitator"),
    ("变异箭毒蛙", "Ranitomeya variabilis"),
    ("奇丽箭毒蛙", "Ranitomeya fantastica"),
    ("草莓箭毒蛙", "Oophaga pumilio"),
    ("丑角箭毒蛙", "Oophaga histrionica"),
    # --- Ranidae: 蛙科 ---
    ("美国牛蛙", "Lithobates catesbeianus"),
    ("美洲豹蛙", "Lithobates pipiens"),
    ("小池蛙", "Pelophylax lessonae"),
    ("虎纹蛙", "Hoplobatrachus tigerinus"),
    # --- Rhacophoridae: 树蛙科 ---
    ("豹纹树蛙", "Rhacophorus pardalis"),
    ("赖氏树蛙", "Rhacophorus reinwardtii"),
    ("斑腿泛树蛙", "Polypedates maculatus"),
    ("斑脚泛树蛙", "Polypedates leucomystax"),
    ("越南苔藓蛙", "Theloderma corticale"),
    ("粗皮苔藓蛙", "Theloderma asperum"),
    ("星点苔藓蛙", "Theloderma stellatum"),
    ("画图夜树蛙", "Nyctixalus pictus"),
    # --- Microhylidae: 姬蛙科 ---
    ("假番茄蛙", "Dyscophus guineti"),
    ("岛番茄蛙", "Dyscophus insularis"),
    ("彩虹蛙", "Scaphiophryne gottlebei"),
    # --- Ceratophryidae: 角蛙科 ---
    ("巴西角蛙", "Ceratophrys aurita"),
    ("苏里南角蛙", "Ceratophrys cornuta"),
    ("斯氏角蛙", "Ceratophrys stolzmanni"),
    ("哥伦比亚角蛙", "Ceratophrys calcarata"),
    # --- Bufonidae: 蟾蜍科 ---
    ("海蟾蜍", "Rhinella marina"),
    ("科罗拉多河蟾蜍", "Incilius alvarius"),
    ("巴拿马金蛙", "Atelopus zeteki"),
    # --- Phyllomedusidae: 泡蛙科 ---
    ("大叶泡蛙", "Phyllomedusa bicolor"),
    ("阿根廷泡蛙", "Phyllomedusa sauvagii"),
    ("虎纹泡蛙", "Phyllomedusa hypochondrialis"),
    # --- Pyxicephalidae: 箱头蛙科 ---
    ("纳塔尔侏儒牛蛙", "Pyxicephalus edulis"),
    # --- Pelodryadidae ---
    ("蓝山树蛙", "Litoria citropa"),
    ("贝氏树蛙", "Litoria booroolongensis"),
]

if __name__ == "__main__":
    print(f"🐍🦎🐸 异宠基因库全量扩展")
    print(f"   蛇 + 蜥蜴 + 蛙 + 守宫 = {len(mod.SPECIES)} 种")
    print(f"   数据源: GBIF + iNaturalist + ReptileDB")
    print(f"   输出: {mod.OUTPUT_FILE}")
    print()
    mod.main()
