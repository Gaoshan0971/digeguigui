#!/usr/bin/env python3
"""异宠批量：蛇/蜥蜴/蛙/守宫"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util

spec = importlib.util.spec_from_file_location("scrape_v3", 
    os.path.join(os.path.dirname(__file__), "scrape_species_v3.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.SPECIES = [
    # 🐍 蛇类
    ("玉米蛇", "Pantherophis guttatus"),
    ("王蛇", "Lampropeltis getula"),
    ("加州王蛇", "Lampropeltis californiae"),
    ("奶蛇", "Lampropeltis triangulum"),
    ("猪鼻蛇", "Heterodon nasicus"),
    ("东部猪鼻蛇", "Heterodon platirhinos"),
    ("黑王蛇", "Lampropeltis nigra"),
    ("灰带王蛇", "Lampropeltis alterna"),
    ("德州鼠蛇", "Pantherophis obsoletus"),
    ("球蟒", "Python regius"),
    # 🦎 守宫
    ("豹纹守宫", "Eublepharis macularius"),
    ("睫角守宫", "Correlophus ciliatus"),
    ("肥尾守宫", "Hemitheconyx caudicinctus"),
    ("巨人守宫", "Rhacodactylus leachianus"),
    ("盖勾亚守宫", "Rhacodactylus auriculatus"),
    ("日行守宫", "Phelsuma grandis"),
    ("洞穴守宫", "Goniurosaurus hainanensis"),
    # 🦎 蜥蜴
    ("鬃狮蜥", "Pogona vitticeps"),
    ("蓝舌石龙子", "Tiliqua scincoides"),
    ("印尼蓝舌石龙子", "Tiliqua gigas"),
    ("绿鬣蜥", "Iguana iguana"),
    ("中国水龙", "Physignathus cocincinus"),
    ("华丽环颈蜥", "Crotaphytus collaris"),
    ("盾甲蜥", "Gerrhosaurus major"),
    ("红泰加蜥", "Salvator rufescens"),
    ("黑白泰加蜥", "Salvator merianae"),
    ("绿安乐蜥", "Anolis carolinensis"),
    # 🐸 蛙类
    ("角蛙", "Ceratophrys ornata"),
    ("南美角蛙", "Ceratophrys cranwelli"),
    ("老爷树蛙", "Litoria caerulea"),
    ("番茄蛙", "Dyscophus antongilii"),
    ("非洲牛蛙", "Pyxicephalus adspersus"),
    ("红眼树蛙", "Agalychnis callidryas"),
    ("牛奶蛙", "Trachycephalus resinifictrix"),
    ("大泛树蛙", "Polypedates dennysi"),
]

mod.DELAY = 1
mod.OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'species_exotics.json')
mod.main()
