#!/usr/bin/env python3
"""批量跑所有龟类品种"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util

spec = importlib.util.spec_from_file_location("scrape_v3", 
    os.path.join(os.path.dirname(__file__), "scrape_species_v3.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# 全部 59 种龟类
mod.SPECIES = [
    ("黄缘闭壳龟", "Cuora flavomarginata"),
    ("草龟", "Mauremys reevesii"),
    ("豹纹陆龟", "Stigmochelys pardalis"),
    ("苏卡达陆龟", "Centrochelys sulcata"),
    ("猪鼻龟", "Carettochelys insculpta"),
    ("钻纹龟", "Malaclemys terrapin"),
    ("巴西龟", "Trachemys scripta elegans"),
    ("鳄龟", "Chelydra serpentina"),
    ("大鳄龟", "Macrochelys temminckii"),
    ("金钱龟", "Cuora trifasciata"),
    ("鹰嘴龟", "Platysternon megacephalum"),
    ("安布闭壳龟", "Cuora amboinensis"),
    ("黄喉拟水龟", "Mauremys mutica"),
    ("花龟", "Mauremys sinensis"),
    ("虎纹蛋龟", "Sternotherus minor peltifer"),
    ("地图龟", "Graptemys pseudogeographica"),
    ("东锦龟", "Chrysemys picta picta"),
    ("西锦龟", "Chrysemys picta bellii"),
    ("红腿陆龟", "Chelonoidis carbonarius"),
    ("黄腿陆龟", "Chelonoidis denticulatus"),
    ("赫曼陆龟", "Testudo hermanni"),
    ("四爪陆龟", "Testudo horsfieldii"),
    ("印度星龟", "Geochelone elegans"),
    ("辐射陆龟", "Astrochelys radiata"),
    ("饼干陆龟", "Malacochersus tornieri"),
    ("靴脚陆龟", "Manouria emys"),
    ("枫叶龟", "Geoemyda spengleri"),
    ("齿缘龟", "Cyclemys dentata"),
    ("黄额闭壳龟", "Cuora galbinifrons"),
    ("锯缘摄龟", "Cuora mouhotii"),
    ("中华鳖", "Pelodiscus sinensis"),
    ("佛罗里达鳖", "Apalone ferox"),
    ("珍珠鳖", "Apalone spinifera"),
    ("圆澳龟", "Emydura subglobosa"),
    ("枯叶龟", "Chelus fimbriatus"),
    ("蛇颈龟", "Chelodina longicollis"),
    ("墨西哥蛋龟", "Staurotypus triporcatus"),
    ("萨尔文蛋龟", "Staurotypus salvinii"),
    ("东部箱龟", "Terrapene carolina carolina"),
    ("斑点池龟", "Clemmys guttata"),
    ("亚达伯拉象龟", "Aldabrachelys gigantea"),
    ("缘翘陆龟", "Testudo marginata"),
    ("缅甸星龟", "Geochelone platynota"),
    ("黑靴陆龟", "Manouria emys phayrei"),
    ("希拉里侧颈龟", "Phrynops hilarii"),
    ("黄头侧颈龟", "Podocnemis unifilis"),
    ("地中海陆龟", "Testudo graeca"),
    ("日本石龟", "Mauremys japonica"),
    ("西非侧颈龟", "Pelusios castaneus"),
    ("剃刀龟", "Sternotherus carinatus"),
    ("麝香龟", "Sternotherus odoratus"),
    ("巨头麝香龟", "Sternotherus minor"),
    ("平背麝香龟", "Sternotherus depressus"),
    ("白唇泥龟", "Kinosternon leucostomum"),
    ("红面泥龟", "Kinosternon scorpioides cruentatum"),
    ("黄泽泥龟", "Kinosternon subrubrum"),
    ("果核泥龟", "Kinosternon baurii"),
    ("牟氏水龟", "Glyptemys muhlenbergii"),
    ("鹰嘴泥龟", "Claudius angustatus"),
]

mod.main()
