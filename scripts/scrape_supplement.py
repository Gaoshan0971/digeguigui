#!/usr/bin/env python3
"""补充：闭壳龟全系 + 缺的陆龟 + 海龟 + 热门水龟"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util

spec = importlib.util.spec_from_file_location("scrape_v3", 
    os.path.join(os.path.dirname(__file__), "scrape_species_v3.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.SPECIES = [
    # ===== 🏆 高闭（闭壳龟铁粉最爱）=====
    ("金头闭壳龟", "Cuora aurocapitata"),
    ("百色闭壳龟", "Cuora mccordi"),
    ("潘氏闭壳龟", "Cuora pani"),
    ("周氏闭壳龟", "Cuora zhoui"),
    ("云南闭壳龟", "Cuora yunnanensis"),
    ("布氏闭壳龟", "Cuora bourreti"),
    ("图画闭壳龟", "Cuora picturata"),
    
    # ===== 🐢 补陆龟 =====
    ("缅甸陆龟", "Indotestudo elongata"),
    ("荷叶陆龟", "Kinixys belliana"),
    ("蛛网陆龟", "Pyxis arachnoides"),
    ("凹甲陆龟", "Manouria impressa"),
    ("安哥洛卡象龟", "Astrochelys yniphora"),
    ("挺胸龟", "Chersina angulata"),
    ("钟纹陆龟", "Kinixys spekii"),
    ("扁尾陆龟", "Pyxis planicauda"),
    
    # ===== 🐢 补水龟/半水 =====
    ("黄头庙龟", "Heosemys annandalii"),
    ("眼斑龟", "Sacalia bealei"),
    ("四眼斑龟", "Sacalia quadriocellata"),
    ("密西西比地图龟", "Graptemys pseudogeographica kohnii"),
    ("南部锦龟", "Chrysemys picta dorsalis"),
    ("星点水龟", "Clemmys guttata"),
    ("欧泽龟", "Emys orbicularis"),
    ("木雕水龟", "Glyptemys insculpta"),
    ("甜甜圈龟", "Pseudemys concinna"),
    ("火焰龟", "Pseudemys nelsoni"),
    ("黄耳龟", "Trachemys scripta scripta"),
    ("格兰德伪龟", "Pseudemys gorzugi"),
    
    # ===== 🌊 海龟（不能养但知识需求大）=====
    ("绿海龟", "Chelonia mydas"),
    ("玳瑁", "Eretmochelys imbricata"),
    ("蠵龟", "Caretta caretta"),
    ("棱皮龟", "Dermochelys coriacea"),
    ("太平洋丽龟", "Lepidochelys olivacea"),
    ("肯氏龟", "Lepidochelys kempii"),
    ("平背龟", "Natator depressus"),
    
    # ===== 🐢 其他热门 =====
    ("平胸龟", "Platysternon megacephalum"),
    ("斑点水龟", "Clemmys guttata"),
    ("牟氏水龟", "Glyptemys muhlenbergii"),
    ("马来闭壳龟", "Cuora amboinensis kamaroma"),
    ("三线闭壳龟", "Cuora trifasciata"),
    ("条颈摄龟", "Cyclemys oldhamii"),
    ("日本地龟", "Geoemyda japonica"),
    ("刺山龟", "Heosemys spinosa"),
]

mod.main()
