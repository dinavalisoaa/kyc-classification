"""Downloads photos from the PAPI CDN (https://cdn.papi.mg/{photo}) to a local folder.

Input: a file listing filenames to fetch (one per line, or CSV with a header, or a JSON
list of strings / list of {"photo": "..."} objects).
Idempotent: a file already present in the output folder is not re-downloaded.

Usage:
    python -m scripts.download_papi photo1.jpg photo2.jpg photo3.jpg   # direct list
    python -m scripts.download_papi --input photos.txt
    python -m scripts.download_papi --input photos.csv --column photo --output downloads
"""
import argparse
import csv
import json
import os
import time

import requests

BASE_URL = 'https://cdn.papi.mg/{}'
DEFAULT_OUTPUT_DIR = 'downloads'
TIMEOUT = 15
MAX_ATTEMPTS = 3

# Hardcoded list: replace with the real filenames.
PHOTOS = [
    '/uploads/logo-papi-picto_ebd274b38743277e9d96921eb6274763839c9f3db7e749c1856db734a7eb7aa3.png',
    '/uploads/logo-papi-full_be3efb0413d80071fbc8f05532d8e414dd0c005b8160c49a39d3c7658921a811.png',
    '/uploads/logo-papi-full_df621b156ba4ce95f27421ae261274f751a38b8fc4dea6be615455eca590b944.png',
    '/uploads/logo-papi-full_96f419bdf0fc7a72b0831748f0030af64c7c5e88c94cf8ecc2cfe9954e07713f.png',
    '/uploads/photo_identite_1c401ef038669caed859a81457db72d1036e175341ef2ae867fb46203efc0818.jpg',
    '/uploads/cin_5af1f57779b0381fc3ceffd4c13dc31acd28f6c0592b857f49167a5f113fc582.jpg',
    '/uploads/certificat_residence_a45eb5d7a153dbb8da0575153e00ef18eb8fd669eace26033b9c271eeebe5672.jpg',
    '/uploads/photo_valencio_3fe703b5d2bf71d7c0f7802aaf268b5eb5c0367d6923be11ffc983596595b1b8.jpg',
    '/uploads/Be_One_CIN_recto-verso_263fe43202eff3359d0099ea9982cd6ea2da55119fcdd9615f2f64650ba2b414.jpg',
    '/uploads/Dirigeant_8e8680c3ba3845f59edf0aff2ad9c653044b466058d55ff07b3951a2aebcbadd.jpg',
    '/uploads/IMG_6347_1__7c39f630ec0ad6bdeba3cfabca1e5c5e3fe110a4a8e7596c60fdb6c2eb5ff3b7.jpeg',
    '/uploads/IMG_6498_1__37db90f24e17c1af21b63044d29ba71e04efba98b8f96d2658abff27640591db.jpeg',
    '/uploads/IMG_6560_1__3b42778b4f7db6c2501a25cb9de5b15317d7a380b5e08e9bcc9cc0fdee9c82e2.jpeg',
    '/uploads/Isaac_Id_e9325b8ea1972d088eed4030243cb84dedb894d003c5ddc89e9cab6520ba1566.jpg',
    '/uploads/identite_34184b51b0b148f1a63edc6269e5a2e4927868870ba055ab02f1ee04e81563b9.jpg',
    '/uploads/Tiana_RAMANANTSIALONINA_a898ee5a4b8a4fd11edc9932235724bea6eb2404be54f5764cb5e3e73d3f798c.jpg',
    '/uploads/Photo_d’identité_Dior_873f4aeeac53f3aa3ed14d30f7b2784a5cecc315f925327a19cbf9d60f89fb54.pdf',
    '/uploads/03149271-0fc3-4cc8-a63e-fb45167b3a1e_c87a1001b8e2b93e8250f54d3e14ea43dc585f407f81e4ce2d18e36f78c23eac.jpeg',
    '/uploads/Photo_6b3721a998e183dfc6ed9071b608e1272c60b8b125e0c958ee6f4c00550c8af2.jpg',
    '/uploads/CIN_24063bf85e536ffdb9e626eec27959fa403070f73d95087514708ee42cc5bf4d.jpg',
    '/uploads/RESIDENCE_9883d194bec947274828d8dff8b21f3e518af965d4ce55807763de99d6c26d9a.jpg',
    '/uploads/Photo_Pro_Buste_897480ebf8bdca86d79a029da9ca8acbe25318cbd98e3b0b220fa1a653e28574.png',
    '/uploads/CIN_Daniel_Aimé_b26f127612ca044bb60f3782f67603a688a236828855d5f2ced21d94e30b9164.jpg',
    '/uploads/Certificat_de_résidence_Daniel_Aimé_ff9f0a8404cba59314758158dd7b8c659cb1bc3675e2e0665ebb91989de4b32a.jpg',
    '/uploads/file_00000000f4b07230b2d2f5c497242156_91e6486b9cd12b00fc65b0ada3b4caaf8a48aa623c107e181b988ebe4e6f54e2.png',
    '/uploads/CIN1_1910af0a5753045d6e5ce992ce6611f985e7b7a8324f2610bbb34d4f4e69a7ed.jpg',
    '/uploads/soutenances~2_205a326b2612955ca36b58f7188aeec1a80a33a2b73af0da181d14ab74ae83eb.jpeg',
    '/uploads/motion_photo_4245255739976300613_0173a3585fef6c8835b54d610d8bf5bdd3bc5599a540d346f07e19df785319fb.jpg',
    '/uploads/Ravalomanda_Ariston_117a6df7497b9cde4c2d9e5607169faf48e695791d3b53055c51ed9cbad4b4af.jpg',
    '/uploads/626047085_1356128086543434_904373523642006476_n_49f170accf18036a86692d1e04dcc50a1800740eaf1194aa34cdbc4ccb133f7b.jpg',
    '/uploads/IMG-20260822-WA0002_a2e37f7761c21e5248b5ba63c3b00ac386d20ea4b5d72891b9596196d7177eb6.jpg',
    '/uploads/IMG-20260822-WA0007_5a15dd9ab6606b4621e000ab13b5937699667f709cbbcb7dff0ef0d252a98d.jpg',
    '/uploads/IMG-20260822-WA0005_0a64a5b22924b32f9a6ab91d1b0fc3f9f65839be353d95c267329e92a656569b.jpg',
    '/uploads/IMG-20260822-WA0003_fc6d2ee90933d24c66cf4d6c3d8fb790e85d85874883fe5ac98eb5770dea563d.jpg',
    '/uploads/Iharizaka_identite_35x45_300dpi_8ff09f6a35813d7dcba639461678711983999d7737a8417240820bf75f94831f.jpg',
    '/uploads/CIN_Iharizaka_Rahaingoson_-_Recto-verso_03ce034fec72483c7da632e56ba6b833ae0a01789382dd09b31b1c1073cf6374.jpg',
    '/uploads/images__2__654b4bdb422dde33ba0cff07434afb08d968c790fcd4490831f1a1431fc6e301.jpeg',
    '/uploads/images_ec38722de6d96ff34260fb503c66bfa13f2267e3532c9546f57022bfa903df5b.jpeg',
    '/uploads/images_035c3e9fd08bc19da619db28c7673030d0ad84843c5eb2dad9e569af70a758bb.jpeg',
    '/uploads/boa_3b4676fe1a6467c41bc3e90e336bec3cb0ddc7071645529ac92d740218e547bf.jpg',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.50.26_5e293e56bb0fb05a4d78dd892a819822378dc298953fc63d37dcc9aa16ef8be6.jpeg',
    '/uploads/CIN_7ab042c824d48add005f7492b8c552d0ca117450ab231fe3a4afcda6f9f0887b.png',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.41.43_12fe7077a7902f7a3a6ddcfb114bb19ff093d03332b7514765cd5c86ccd21e8f.jpeg',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.49.33_3690f9796f4b3681c4afe68777cad390c5ac2ae990555efcca1a1eaed5e64e62.jpeg',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.49.33__1__15ac2519539ba809f142b8897a3a34a5e1c16b03a61b93a3067f7603c2b7e453.jpeg',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.49.33_9c4acdf8dc419b0b7819f2ba3951e074f0feb7ac25fd6c045165ee376c0cedfa.jpeg',
    '/uploads/Statut_a14c0b91b6c6cc6ab75d36446480d598654351ed0e4d7ae443067eb603482345.png',
    '/uploads/CIF-1_3039f5a2308184bf54a356f27493c8d1b6cc5bb62f51f37f05d41f9e2489c5f0.jpg',
    '/uploads/STAT_e50c42efadf28120ae01ab53018c07e8b721255025ab94447352aec16fdde096.png',
    '/uploads/RCS_6cef9e67f57ceb3d0b66315d7059ec39f6ce781e31d820c4c520a372dc6893e5.png',
    '/uploads/PXL_20260815_071431251_dc9a9ef0237d334abb625fff7714952cabd21cfe500c574e83da23fbb996b20d.jpg',
    '/uploads/IMG-20260727-WA0000_b8fc69c64d36c16ab59fa4474ebf34d9620f17bd30c0f4f820b5602c233677a8.jpg',
    '/uploads/My_Photo_4x4_58120f2b2d4406187d0a0e8b3e8e239bc383dc316c0609f4b3f983ab4258e72a.jpg',
    '/uploads/CIN_recto_&_verso_753e344a3e6c0873f40348b1e98abb8078d89fbc457e0379b9669752134e0cfb.jpg',
    '/uploads/IMG_20260810_124347_bff1d519d5139dd40c483d30fb25c166e590959b1168a893842628b8430c6d10.jpg',
    '/uploads/Média__2__b0119c88e02eb52626142dcd5d4805783e170fb9eaabe449b11bade3540e6297.jpeg',
    '/uploads/CIN_2.0_23959b8540b227be7552c84ec771fbb907786eab05eabf1473b716505359ed80.jpg',
    '/uploads/Photo_Patrick_Deleurme_f30e3cdb8b9bba83b84b4ba8e5bd647ce09b3059db72eef4e71e1b2d38b65727.jpeg',
    '/uploads/Carte_résident_Patrick_DELEURME-recto_5d864d15d07e196b4a9a4bdbb900d845ef98dac788877bdaf1da4b9258e65fcb.jpg',
    '/uploads/_Certificat-de-résidence-12-09-2026_4be31b2b36d5dcfef04f4beb1434aa82d05d9e3190803d210a6855e210b0112e.jpg',
    '/uploads/Untitled_eb1024853bcd3c5d55a96f41bd0e7662004e3dba41c0ab60e329fdf91cbf0637.jpeg',
    '/uploads/CIN_848cf975d89528ecc3d4183c4d023bd65e77693d4974d68a75480680af71f188.jpeg',
    '/uploads/residence_7f4a7bc869a85c8aa3799cbf62e796143885a6ca28a97ebcfaa64776f5928338.jpeg',
    '/uploads/logo-papi-picto_ebd274b38743277e9d96921eb6274763839c9f3db7e749c1856db734a7eb7aa3.png',
    '/uploads/logo-papi-full_be3efb0413d80071fbc8f05532d8e414dd0c005b8160c49a39d3c7658921a811.png',
    '/uploads/logo-papi-full_df621b156ba4ce95f27421ae261274f751a38b8fc4dea6be615455eca590b944.png',
    '/uploads/logo-papi-full_96f419bdf0fc7a72b0831748f0030af64c7c5e88c94cf8ecc2cfe9954e07713f.png',
    '/uploads/photo_identite_1c401ef038669caed859a81457db72d1036e175341ef2ae867fb46203efc0818.jpg',
    '/uploads/cin_5af1f57779b0381fc3ceffd4c13dc31acd28f6c0592b857f49167a5f113fc582.jpg',
    '/uploads/certificat_residence_a45eb5d7a153dbb8da0575153e00ef18eb8fd669eace26033b9c271eeebe5672.jpg',
    '/uploads/photo_valencio_3fe703b5d2bf71d7c0f7802aaf268b5eb5c0367d6923be11ffc983596595b1b8.jpg',
    '/uploads/Be_One_CIN_recto-verso_263fe43202eff3359d0099ea9982cd6ea2da55119fcdd9615f2f64650ba2b414.jpg',
    '/uploads/statut_be_one_sarlu_moins_de_2Mo_5b0f8b53b19a7d072a8642850252a4166b26fc1ac3ba6176340bf38eee37de75.pdf',
    '/uploads/NIF_Be_one_sarlu_c2ee49a6014b609ed7ad4c0888036e7c85f6dd166efafc61343bfbc5e11649fa.pdf',
    '/uploads/carte_statistique_be_one_sarlu_c4e7eee825412cb80bd7225df8078ac757ca39c84af39ef64983b9a41a2a05ee.pdf',
    '/uploads/rcs_be_one_sarlu_f17788cba51cb46fe8aac50a9b6485907ca0cc75e249888e4dcbad2b11ea39e3.pdf',
    '/uploads/Certificat_de_conformite_FMaM_e1c781a24316203b5b5e7988839a754558bb8d032398696617b8eedfe0fab154.pdf',
    '/uploads/Statut-FMaM-1_100d6324a910904de0fabbd4041036203a1a9998f6bef95018b1d66867500de8.pdf',
    '/uploads/CIF_FMaM_0cd380586c5942a911e057202657ea8f5dd9253f04218553e1fbaa76bb984c0e.pdf',
    '/uploads/recepossé_spope_92f12319bdb90dfcb209d801d1a26d9cff71cedf456e8e054716202a1143e01f.pdf',
    '/uploads/Status_ok_af6b02481e8f275eac2e7840bb78f397753475866c00b7f0301230c742cdef1a.pdf',
    '/uploads/Dirigeant_8e8680c3ba3845f59edf0aff2ad9c653044b466058d55ff07b3951a2aebcbadd.jpg',
    '/uploads/CIN_9ccb827b1ef06b37ddacd06c0b2726c8c502d66a1892ffad19627dd5e289d42b.pdf',
    '/uploads/RESIDENCE_bb7bd19e2998489d5053ebc68c788225803e1ebf90957f2424984dce1fbd45f7.pdf',
    '/uploads/IMG_6347_1__7c39f630ec0ad6bdeba3cfabca1e5c5e3fe110a4a8e7596c60fdb6c2eb5ff3b7.jpeg',
    '/uploads/IMG_6498_1__37db90f24e17c1af21b63044d29ba71e04efba98b8f96d2658abff27640591db.jpeg',
    '/uploads/IMG_6560_1__3b42778b4f7db6c2501a25cb9de5b15317d7a380b5e08e9bcc9cc0fdee9c82e2.jpeg',
    '/uploads/Isaac_Id_e9325b8ea1972d088eed4030243cb84dedb894d003c5ddc89e9cab6520ba1566.jpg',
    '/uploads/ID_CARD_Ruben_new_439a47b454ed7a3c953c2a23240ab76ac9ce657ff3e35e5ab4798bdc4e99b394.pdf',
    '/uploads/certificat_de_résidence_mada_isaac_d22c9a2ead5466fdbeaa3fa1712c23a24906d52ea7f11c0a98624086ba625d28.pdf',
    '/uploads/CIF_ZEBU_AIR_2025.docx_3d8246f4c0711504429807eb6b4fd75f2d45ff6f9bd1a623d28f158b7211eb28.pdf',
    '/uploads/RCS_zebu_air_ae9238799df8fbbcd12d8279c06cddf7ddaaab1bc657a1bb1e3592c2815586fa.pdf',
    '/uploads/identite_34184b51b0b148f1a63edc6269e5a2e4927868870ba055ab02f1ee04e81563b9.jpg',
    '/uploads/kyc_51bb0210686ef95ae5bab792bb82120015644e076b45c5568566ec025e69e309.pdf',
    '/uploads/Tiana_RAMANANTSIALONINA_a898ee5a4b8a4fd11edc9932235724bea6eb2404be54f5764cb5e3e73d3f798c.jpg',
    '/uploads/CIN_Tiana_942211a03483c47b34f98ec6c276bb759977291e02cefa4610523f9c193a886e.pdf',
    '/uploads/Statut_Societe_9385b4f2d52e886aeb1f868386cfd7dd907dba14d72ab0feac164e68fb7a924d.pdf',
    '/uploads/NIF__155d83e99e58d2c5f042d046f1afd8e259d49a494b50eecdbae05081dbf1f993.pdf',
    '/uploads/STATISTIQUE_f385bda813b0c54fb315403ef7094c0cdacc39096b2fec1722f40d58458cd1ce.pdf',
    '/uploads/RCS_cca21439a096f1a705687cffdca6100c88bb970e5e41acc51e3f6169b0c8ef2e.pdf',
    '/uploads/Photo_d’identité_Dior_873f4aeeac53f3aa3ed14d30f7b2784a5cecc315f925327a19cbf9d60f89fb54.pdf',
    '/uploads/CIN_DIOR_2be7b18c18c768de87a1a4fb2288ae4c69f56fa04ca6a22247e6ad16526e945b.pdf',
    '/uploads/CERTIFICAT_DE_RESIDENCE_DIOR_08c780c80d60c64fd91abd938010bf0e84dd764857e792f353338d8c6fc3dcee.pdf',
    '/uploads/Statu_9b71261b6b9073b0cd9e3802805c3bf84c71759a60dcc1649e2d81ba8cb5e5be.pdf',
    '/uploads/Identification_Fisacle_0c658c605af2de602b16b9f62006b00ced6012536f488cac532dd4c062ea7a98.pdf',
    '/uploads/CARTE_STATISTIQUE_compressed_fb81c209be7b9b1722848d0a3539133d36267036697e13834a4c456f312afb2d.pdf',
    '/uploads/03149271-0fc3-4cc8-a63e-fb45167b3a1e_c87a1001b8e2b93e8250f54d3e14ea43dc585f407f81e4ce2d18e36f78c23eac.jpeg',
    '/uploads/Photo_6b3721a998e183dfc6ed9071b608e1272c60b8b125e0c958ee6f4c00550c8af2.jpg',
    '/uploads/CIN_24063bf85e536ffdb9e626eec27959fa403070f73d95087514708ee42cc5bf4d.jpg',
    '/uploads/RESIDENCE_9883d194bec947274828d8dff8b21f3e518af965d4ce55807763de99d6c26d9a.jpg',
    '/uploads/Photo_Pro_Buste_897480ebf8bdca86d79a029da9ca8acbe25318cbd98e3b0b220fa1a653e28574.png',
    '/uploads/CIN_Daniel_Aimé_b26f127612ca044bb60f3782f67603a688a236828855d5f2ced21d94e30b9164.jpg',
    '/uploads/Certificat_de_résidence_Daniel_Aimé_ff9f0a8404cba59314758158dd7b8c659cb1bc3675e2e0665ebb91989de4b32a.jpg',
    '/uploads/file_00000000f4b07230b2d2f5c497242156_91e6486b9cd12b00fc65b0ada3b4caaf8a48aa623c107e181b988ebe4e6f54e2.png',
    '/uploads/CIN1_1910af0a5753045d6e5ce992ce6611f985e7b7a8324f2610bbb34d4f4e69a7ed.jpg',
    '/uploads/soutenances~2_205a326b2612955ca36b58f7188aeec1a80a33a2b73af0da181d14ab74ae83eb.jpeg',
    '/uploads/karapanondro_3e4cafed9af7de32dfe5d964454deeb0b98221c754b665ec117870356de4f766.pdf',
    '/uploads/motion_photo_4245255739976300613_0173a3585fef6c8835b54d610d8bf5bdd3bc5599a540d346f07e19df785319fb.jpg',
    '/uploads/Ravalomanda_Ariston_117a6df7497b9cde4c2d9e5607169faf48e695791d3b53055c51ed9cbad4b4af.jpg',
    '/uploads/CIN_Ariston_852130dac8eaafd2e372b985ee099faed5fa5de1745b0a2e7904f9c09a682c01.pdf',
    '/uploads/résidence_0bb962829fe169a7bd34e736c901e1f6d079665005c74ede8a7980c9bcdd7005.pdf',
    '/uploads/626047085_1356128086543434_904373523642006476_n_49f170accf18036a86692d1e04dcc50a1800740eaf1194aa34cdbc4ccb133f7b.jpg',
    '/uploads/CIN_Naomy_4b0a5246aa2ded4eb901e789bc338fc90d44e32a8aa784beccb6f82c4c81d1a4.pdf',
    '/uploads/Residence_Boteo_a6d1fd26e38826f2e037f199f109c4a232666bd6c6e84e9cb5856ec9dab3d554.pdf',
    '/uploads/Statut_Boteo_ec0029c238812e7e42560eade698f5e150e8d853f7450f9c0d99c223d9be14cf.pdf',
    '/uploads/Nif_Boteo1_1fa7ac54c049be50ca404375e28f2cb960a1e51c674207d208ee7ef9eede05b5.pdf',
    '/uploads/Stat_Boteo_1_abae46d3211be459aaac079bb9c9aa157e4c94a160d0c789e6f599f29c40ff92.pdf',
    '/uploads/RCS_Boteo_ba54d83c45d954aa2bc1ccdfa00e4a565bad2d4b4cfa3febd29fa0f44664c7c7.pdf',
    '/uploads/IMG-20260822-WA0002_a2e37f7761c21e5248b5ba63c3b00ac386d20ea4b5d72891b9596196d7177eb6.jpg',
    '/uploads/IMG-20260822-WA0007_5a15dd9ab6606b4621e000ab13b5937699667f709cbbcb7dff387ef0d252a98d.jpg',
    '/uploads/IMG-20260822-WA0005_0a64a5b22924b32f9a6ab91d1b0fc3f9f65839be353d95c267329e92a656569b.jpg',
    '/uploads/IMG-20260822-WA0003_fc6d2ee90933d24c66cf4d6c3d8fb790e85d85874883fe5ac98eb5770dea563d.jpg',
    '/uploads/Manuscrit_2026-08-25_153654_dd1dc8748b307619773b9c6ded216363c8fd6c315f29ce261fb235c06ee5107a.pdf',
    '/uploads/Iharizaka_identite_35x45_300dpi_8ff09f6a35813d7dcba639461678711983999d7737a8417240820bf75f94831f.jpg',
    '/uploads/CIN_Iharizaka_Rahaingoson_-_Recto-verso_03ce034fec72483c7da632e56ba6b833ae0a01789382dd09b31b1c1073cf6374.jpg',
    '/uploads/2025-03-12_Certificat_de_résidence_Iharizaka_Rahaingoson_682f7537ffb247ae61672cdb48ca80782118803e58a9113a56f29e96ec608664.pdf',
    '/uploads/IBONIA_-_Statuts_mis_à_jour_du_01_03_2019_enregistré_9a1599a607f65c3974509859a926b8617a96ce4d762db7a4f2dfd24b1724a41b.pdf',
    '/uploads/Carte_CIF_Ibonia_2025_e432753c8e627361617310af1a3ef796fe075e7fe2f4c3e91e8e531f3e15176c.pdf',
    '/uploads/Ibonia_carte_statisitique_c5ded83d93c80ecebedc950a02460c8c3263b4669b6307e91467173ee30d1b77.pdf',
    '/uploads/Ibonia_RCS_fa76b0bd20a558840a3f0509929cd2f1953f03d2dcb0c0f93dd41ba920f3a5c1.jpg',
    '/uploads/images__2__654b4bdb422dde33ba0cff07434afb08d968c790fcd4490831f1a1431fc6e301.jpeg',
    '/uploads/images_ec38722de6d96ff34260fb503c66bfa13f2267e3532c9546f57022bfa903df5b.jpeg',
    '/uploads/images_035c3e9fd08bc19da619db28c7673030d0ad84843c5eb2dad9e569af70a758bb.jpeg',
    '/uploads/boa_3b4676fe1a6467c41bc3e90e336bec3cb0ddc7071645529ac92d740218e547bf.jpg',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.50.26_5e293e56bb0fb05a4d78dd892a819822378dc298953fc63d37dcc9aa16ef8be6.jpeg',
    '/uploads/CIN_7ab042c824d48add005f7492b8c552d0ca117450ab231fe3a4afcda6f9f0887b.png',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.41.43_12fe7077a7902f7a3a6ddcfb114bb19ff093d03332b7514765cd5c86ccd21e8f.jpeg',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.49.33_3690f9796f4b3681c4afe68777cad390c5ac2ae990555efcca1a1eaed5e64e62.jpeg',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.49.33__1__15ac2519539ba809f142b8897a3a34a5e1c16b03a61b93a3067f7603c2b7e453.jpeg',
    '/uploads/WhatsApp_Image_2026-08-17_at_15.49.33_9c4acdf8dc419b0b7819f2ba3951e074f0feb7ac25fd6c045165ee376c0cedfa.jpeg',
    '/uploads/Statut_a14c0b91b6c6cc6ab75d36446480d598654351ed0e4d7ae443067eb603482345.png',
    '/uploads/CIF-1_3039f5a2308184bf54a356f27493c8d1b6cc5bb62f51f37f05d41f9e2489c5f0.jpg',
    '/uploads/STAT_e50c42efadf28120ae01ab53018c07e8b721255025ab94447352aec16fdde096.png',
    '/uploads/RCS_6cef9e67f57ceb3d0b66315d7059ec39f6ce781e31d820c4c520a372dc6893e5.png',
    '/uploads/PXL_20260815_071431251_dc9a9ef0237d334abb625fff7714952cabd21cfe500c574e83da23fbb996b20d.jpg',
    '/uploads/IMG-20260727-WA0000_b8fc69c64d36c16ab59fa4474ebf34d9620f17bd30c0f4f820b5602c233677a8.jpg',
    '/uploads/My_Photo_4x4_58120f2b2d4406187d0a0e8b3e8e239bc383dc316c0609f4b3f983ab4258e72a.jpg',
    '/uploads/CIN_recto_&_verso_753e344a3e6c0873f40348b1e98abb8078d89fbc457e0379b9669752134e0cfb.jpg',
    '/uploads/IMG_20260810_124347_bff1d519d5139dd40c483d30fb25c166e590959b1168a893842628b8430c6d10.jpg',
    '/uploads/Résidence_00_5fb6448b2802d3e21d7fdd081288018137b9fb71c34d4dc1021a0f5d4c55ba4e.pdf',
    '/uploads/Média__2__b0119c88e02eb52626142dcd5d4805783e170fb9eaabe449b11bade3540e6297.jpeg',
    '/uploads/CIN_2.0_23959b8540b227be7552c84ec771fbb907786eab05eabf1473b716505359ed80.jpg',
    '/uploads/CIN_1_8171533ff2099ba646f3b67d17ad0cde0e834319bcb1a1f9a777189487e9d7f4.pdf',
    '/uploads/STATUT_WATERGATE_MODIFIE_b21ad7a5a0adb1956aff80812a358c0afc1e4c308c2c9bab2e5dfcef24b95b01.pdf',
    '/uploads/NIF-STAT-RCS-RIB__1__compressed_de202561cf948d60dd34b54325f0c70795864a14c037d70def4dbc7acf2ac6e1.pdf',
    '/uploads/NIF-STAT-RCS-RIB__1__compressed_776ffc78a7017bbfa2e82abf5402d6fe57f50bc5283e55317a33ff73e3ce62d3.pdf',
    '/uploads/WATERGATE_4_Extrait_RCS_gerant_HAREL_fca4917bb499bd2254ccdd9eea66cd4e41a1e9b26009237e4fb357962b35c00d.pdf',
    '/uploads/Média_e9f5e9d7e7d6cfcfa18fc1ac9c8e5c20115f9b7073cf0dd5f7782bb8fe63ac88.jpg',
    '/uploads/Doc1__1__90a68b50cb02eab52498fa6f8578a5616614f0a9d5aa3d6126f9054a358f9e51.jpg',
    '/uploads/1000015785_6b91644fde3537769c01e7ee4260919c8df92f994a323d86ccc3ba8961bb58aa.jpg',
    '/uploads/Edited_2_d11dc296d468233885b3450af5e21e0874f84ea9c8f78b09b21bedad06f58ccd.png',
    '/uploads/CIN_FANIRIANTSOA_cd4fb6f7dcd5758cbae64ac767d70385f19796133f1b0652ceaefbbe00eb1c56.pdf',
    '/uploads/Certificat_de_residence20260911_08290313_37d3bbcde8712b5328fbff97e5a258e9cee68c6338ea34b128088cef02fab1cf.pdf',
    '/uploads/WhatsApp_Image_2026-09-22_at_11.02.15_ebd3ae5e489c8379ebb09b376ed4df695c07e592b297860dc43cc0053e890397.jpeg',
    '/uploads/WhatsApp_Image_2026-09-22_at_11.01.10_d1d328527a0f94c82279734f1f91885280e1816002d025a37e56b8c252067dac.jpeg',
    '/uploads/STATUT_DP_compressed_dd328289888bccdc1de86e873be30a640723007180873312bdd6217ca9b6a5fe.pdf',
    '/uploads/CIF_DernierPrix_2026_db2e1413eb574e94e4d3473bd0a612a471460d09c280d1a321dcaecda874a581.pdf',
    '/uploads/Stat__1__ddcd44e894d4b11f909e20f79c533ffafc5a98effaab061c1ee444e80b689c7e.pdf',
    '/uploads/RCS_DernierPrix_44f1aa5fecd4939180bb04e40e1ae50066ca6efc95044e49c379aa0bceed656f.pdf',
    '/uploads/6rZ66X-B_77de67255460da861aaace2700be9649df3586f5e84330a5be1ca1d540e609e8.jpg',
    '/uploads/6rZ66X-B_3bf11af6740be485994d23c65dbb2857376d201d50dfc399618da6d2f5d86db1.jpg',
    '/uploads/6rZ66X-B_f5efe847b1f0ee8d63f3bf48a9e0cce80fa9193dec16a47475f56d386733b095.jpg',
    '/uploads/Passeport_Thimothee_HOUNDJO_8ee1a232bd130662bd42f87272286a1eec76d66699d1a977b26f4f169c84ca28.pdf',
    '/uploads/Statuts_MiMo_Global_MG_SARLU_High_24d3ef54100cc50b45a4e4a749e7af9679bb0e156d8217016be73785a34c8ffd.pdf',
    '/uploads/Carte_fiscale_2026_NIF_3020053838_aaa0daaf0a1c036213b78414c8f3a3b47a9e89754c721ff3bce263b9944db334.pdf',
    '/uploads/Carte_statistique_INSTAT_2026_756af00f3b0aa51e68dd4eae86fb05dc2936a18648c28bf3e7bf009c1c9b6ae5.pdf',
    '/uploads/Extrait_RCS_Antananarivo_2026_B_01173_53991946b645d8c112682b4d92c7d0d120086c4f5483abf11a8704726b99b62e.pdf',
    '/uploads/IMG_20251016_064744_995_11zon_d8b878c3c034087ff93b864e343b94944b5b741c278bfad6627fa047f8548b17.jpg',
    '/uploads/CIN__1__353194d6a44e5e3fd00661b99c13b1767e06390adeda69dc7131eba4812a484b.jpg',
    '/uploads/IMG_3976_c0ba1a486b51c605c08c38e2d0fa15d1c9d73ba3761afc2612d3f7130e4eb7b4.jpeg',
    '/uploads/CIN_a0c989414e60c636a56fdf6795f37bc6b0703edfe64e6c5f3cbc579786d104cb.pdf',
    '/uploads/Certificat_de_residence_3f39508f74d82d9877dbff686e3980fec297f93126335c174b42cab3b7d6d9f0.pdf',
    '/uploads/Portrait_Kekee_trois-quart_2ee171f511b608a02a526cbf77e3d3c8035ad8960228016197904667e453c649.jpg',
    '/uploads/CIN_Bodo_Ratsihosena_recto-verso_200dpi_c2d45bb120d8ad10042d8111d4a6a324eb6508543fc5b3017e8b4075edeea906.jpg',
    '/uploads/Certificat_de_résidence_Iharizaka_Rahaingoson_2025-03-12_b0eee44d6059fcacd2b3f0e39cb857ebc9275608773a95f17e0256ede90c07b2.jpg',
    '/uploads/FACE_c18d1ba8c3160dbf64a85357a4f171abb3b95af0d924dc6f668a553bbf781b60.jpg',
    '/uploads/FACE_9c9280170e84d7013401299022c6fbb8a58a6878bca512eac87954f095ebb015.jpg',
    '/uploads/IMG_20260910_090041_a1488fad63a77f2fd7a4f8f6700ec12473b2dd31893e0b8f5fea616b1054a2c8.jpg',
    '/uploads/IMG_20260910_090041_7f5c6701e5195d4169bb57f906bfd841e4c134c4d0c6476d12361786529d164c.jpg',
    '/uploads/Projet_Statuts_Tafass_SARLU-1_801053381ae7b2cf3ce38fa1fa8be079efbb7e9cc515e94d744700a1169f515a.pdf',
    '/uploads/Projet_Statuts_Tafass_SARLU_Adresse_MAJ_3d0a9d07ffe81748d5c56a827c64c39ffc899c5226758b2dc70b75211aa97f1a.pdf',
    '/uploads/image_fe9b916ddd180c319df6f4f33cfff3c634a7335ef15a9e353bbe26ce3fa128f0.jpg',
    '/uploads/file_00000000572882119b89bb8c06d7b2aa_f54c4851cc041fd3a079c807e67b9509a4617ed85391bf0028cf2a49bb700974.png',
    '/uploads/CIN_recto-verso_6f28a3a3c02b8b6501d0bd6c5e3d4ce126f3694d595af3ecfebb65036828e1ce.jpg',
    '/uploads/20260912_083904_48ad8a8be4214232474a8906a60358911ba09bd992566fb8fa4036374ea407d1.jpg',
    '/uploads/FACE_407066a7d9047c9be6fd03f797f779168802c6b8f69e618439ea87317d71ae74.jpg',
    '/uploads/FACE_c21955819ab3f6698a9a21263ae18b7ff1d6eff6dbe602d7da81c5328f855389.jpg',
    '/uploads/residence_6b92c77f4983b3360e1218041cdc20164f2fc28cc1ff1569915a5cac750b2cb9.jpg',
    '/uploads/IMG_3700_b4076438e9f6901483d43974756e714d66ed8944a1d314c87d764d7488d8b644.jpeg',
    '/uploads/1771259397_cb9379d89b92d8b9879bc2267a07d50d10a4a9234e0bec7db6b27222220fc65a.pdf',
    '/uploads/Document_numérisé_6_3f6001f8015b27f905e6a65b8905f88774617348883870853bb4b58581cb6dc6.pdf',
    '/uploads/Iharizaka_identite_35x45_300dpi_1c84671f2f9b9f38a4bd84731e057a1c2f8ceda58a8def49ddeb4262b97ced99.jpg',
    '/uploads/CIN_Iharizaka_Rahaingoson_-_Recto-verso_733874b04f35fe77a3f56683c7de1b25ab3528b6e26587f2cca4906e08b79361.jpg',
    '/uploads/Certificat_de_résidence_Iharizaka_Rahaingoson_2025-03-12_97846303edeac6cd93c79285364b659345494d51213a1fa3b86ababd58a1aa8b.jpg',
    '/uploads/Photo_d\'identité_7d3a1f7b88eeb1f172e4bfd9ea0183bec51ea65d5a8d9eb92141539ecd12f6ae.jpg',
    '/uploads/CIN_recto-verso_c2b4402666c2949d9a05fe16958b4624d96dbd45737aa6d3d1771fa9196e8b03.pdf',
    '/uploads/Photo_41858a78dc849d9ae52d9a69684e2f252c36ba4fb33ed28c6854c55e8c493868.PNG',
    '/uploads/CIN_6bca9c541addcd5397a467d40c3f156c23696ecaa9a3f57b64bdbe7070b1e6d0.pdf',
    '/uploads/Certificat_Residence_8349bf6dacce3886cab690be03722446c12fca87e714c164d590606edd9af138.jpg',
    '/uploads/Goudz_CIF_0d406dd72505c9ff6ebe040104cd0711954ecfdcbaa7640ef39cb99f4121a8be.pdf',
    '/uploads/Goudz_Stat_218f7f59b690f90acffc640688a86d2478643a2313daa50b414cfd5196dc00f2.pdf',
    '/uploads/RCS_8872040362f483efca9cc0929a361862bc5abae4d842de3c4588227816987122.pdf',
    '/uploads/RAMIAKAMANANA_-_SALOHINIAINA_MIREILLE_-_PHOTO_-_2_97614b21e52807f2cf52051757bf7607fd21f23c7743c5072c1089ce582ad925.jpg',
    '/uploads/RAMIAKAMANANA_SALOHINIAINA_CIN_2_4296c71aad0599f5ed7a0be7d2d5fe1248c983230ea00da5cb0cb53e72f4f58a.pdf',
    '/uploads/CERTIFICAT_DE_RESIDENCE_d5a0dd903fb132c4e0a90b69323069208cb5a951abc15526799cb74316bb50aa.pdf',
    '/uploads/Capture_d’écran_2026-09-17_à_12.34.16_4a1ce07cc9592864871e134933e2cb1e33d487d0822b81e5bb9a943c6a072906.png',
    '/uploads/Capture_d’écran_2026-09-17_à_12.43.17_167370740fd449854b8cc09673474eec513a2140dea2d278d8c1470d5606f88d.png',
    '/uploads/Capture_d’écran_2026-09-17_à_15.11.31_31b2dbb212875ecef3780024d89f61e004c9c5b19e624c93435b48754d2bdecb.png',
    '/uploads/Capture_d’écran_2026-09-17_à_11.54.44_53e5644ac16b72ea5f5f2c3138855cc2333116d625eb01e4113305b89f5003ff.png',
    '/uploads/Capture_d’écran_2026-09-17_à_11.55.28_14508ebac6b6cd54493121fb2d444624069821f8b8bde5a3e88251dc334374f5.png',
    '/uploads/Capture_d’écran_2026-09-17_à_15.25.16_428a8aa43a19828caaae2f37e937c50b1ac55f29842de6dc34235a6df2aeaee6.png',
    '/uploads/sary_tapaka_d672da11c10660d4cc69757df8e990e95a6a3eb2f9d8ee39ac9a48c513e83b3b.jpeg',
    '/uploads/IMG-20260422-WA0008~2_a22411babd118b6d338c3027975b43fda1178700800828ddba646fff33ca0641.jpg',
    '/uploads/IMG_20260427_155833732_1__444c7df2999f759bbdff0b876c098b913b1655a27080d28f455ed930e1be0d97.jpg',
    '/uploads/Gemini_Generated_Image_tc5zctc5zctc5zct_e9b3d0d2529fa54fab66a71da2c64f9de1b97f671d3ed2f1aef3d2c9cafa07d4.png',
    '/uploads/CIN_ORIGINAL_VERSION_NUMERIQUE~1_9540642d4f2183c27f40d9ba90d7848b9ba674d14cc3b212f8d67fcc51fae425.jpg',
    '/uploads/img20260918_15463206_d708dfc69e119fa16a88100a1e4b069c4699cba489d70eac8c023a980448ea8d.jpg',
    '/uploads/image_16d90c18259f74178076e91fedd9fe9c0b1f8ac0aa90f9a83213b878d7601056.jpg',
    '/uploads/Untitled_design_cc0b77d618afaa2fbcea8630a5a035ab3921941062c145417c5b401257078c37.jpg',
    '/uploads/IMG_20260831_165433__1__e1f4d52c399d4a2e809f815f6f4c9d6b1c2884178d9485afd8a14156b3eb5acf.webp',
    '/uploads/STATUT_RICEFIELD_VALLEY_42146047583ead2abe24ac5b0ef3314c0a2ce6fbc2e097b23b203a0e9451c649.pdf',
    '/uploads/NIF_Ricefield_3e9c1f1e38d9e9ba11527fbd8f19467c1b21796c6218d5aa742721c551d11fe8.pdf',
    '/uploads/Statistique_RICEFIELD_VALLEY_76ad609878c486be1028df077538191da294af57f8a1e6818cd3ddce65567709.pdf',
    '/uploads/IMG_20260921_090317_79c89427284540ba9582575da672b97658ab707c439b0cdda746ebe4958b44b6.jpg',
    '/uploads/1000001909_e25a5de077ae63088544c82b04c2c0a848a9af98b30352a7e3b80a49bd00d29a.pdf',
    '/uploads/IMG_20260922_154245_3525af033198fd4ec95127c9323cabdaa1486bb6d350e404332a29300134ad82.jpg',
    '/uploads/1000002063_bdb0b49a151446154a15a1ed90b9c43bf4caa7ef100d7bd82d60ce28e0d67df2.pdf',
    '/uploads/1000002066_62e4cba2c1a1337e4a723aa6c1dd145c67a1f8e06a0b03080076e5766924fb76.pdf',
    '/uploads/Photo_Patrick_Deleurme_f30e3cdb8b9bba83b84b4ba8e5bd647ce09b3059db72eef4e71e1b2d38b65727.jpeg',
    '/uploads/Carte_résident_Patrick_DELEURME-recto_5d864d15d07e196b4a9a4bdbb900d845ef98dac788877bdaf1da4b9258e65fcb.jpg',
    '/uploads/_Certificat-de-résidence-12-09-2026_4be31b2b36d5dcfef04f4beb1434aa82d05d9e3190803d210a6855e210b0112e.jpg',
    '/uploads/2026_STATUTS_WEBIA_SARLU_MISE_A_JOUR-2026-v-web_596251efe8fa435f9d18a6c46313a364bc5eaf56717d720a2f8bbaf91e359dd6.pdf',
    '/uploads/2025_NIF-Webia__1f9c8557e3ef6d705fcd2c3b0d9ccffecdba080165425f147c03172dd38b7120.pdf',
    '/uploads/2026_STAT_WEBIA_A_JOUR_2026_3f8e54e5664e4b24e857e4afdbaf7ea7fb1ff7bd865b8bea96e06818373dab89.pdf',
    '/uploads/2026_RCS_WEBIA_A_JOUR_2026_fd65eabd62f9aaa666bdc0d42cc618629b6e6ff1eec6c7e9d28c39ee74c9b240.pdf',
    '/uploads/Untitled_eb1024853bcd3c5d55a96f41bd0e7662004e3dba41c0ab60e329fdf91cbf0637.jpeg',
    '/uploads/CIN_848cf975d89528ecc3d4183c4d023bd65e77693d4974d68a75480680af71f188.jpeg',
    '/uploads/residence_7f4a7bc869a85c8aa3799cbf62e796143885a6ca28a97ebcfaa64776f5928338.jpeg',
]


def read_list(path, column):
    ext = os.path.splitext(path)[1].lower()
    with open(path, encoding='utf-8') as f:
        if ext == '.json':
            data = json.load(f)
            return [d[column] if isinstance(d, dict) else d for d in data]
        if ext == '.csv':
            reader = csv.DictReader(f)
            return [row[column] for row in reader]
        # .txt or other: one name per line
        return [line.strip() for line in f if line.strip()]


def download_one(session, photo, output_dir):
    destination = os.path.join(output_dir, os.path.basename(photo))
    if os.path.exists(destination):
        return 'already_exists'

    url = BASE_URL.format(photo)
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            r = session.get(url, timeout=TIMEOUT)
            if r.status_code == 404:
                return 'not_found'
            r.raise_for_status()
            with open(destination, 'wb') as f:
                f.write(r.content)
            return 'ok'
        except requests.RequestException as e:
            last_error = e
            time.sleep(1.5 * attempt)  # simple backoff
    print(f'FAILED {photo}: {last_error}')
    return 'failed'


def download_photos(photos, output_dir=DEFAULT_OUTPUT_DIR):
    """Usable from another script: download_photos(['a.jpg', 'b.jpg'])."""
    os.makedirs(output_dir, exist_ok=True)
    print(f'{len(photos)} photo(s) to process -> {output_dir}')

    counts = {'ok': 0, 'already_exists': 0, 'not_found': 0, 'failed': 0}
    with requests.Session() as session:
        for i, photo in enumerate(photos, 1):
            status = download_one(session, photo, output_dir)
            counts[status] += 1
            print(f'[{i}/{len(photos)}] {photo}: {status}')

    print('---')
    for status, n in counts.items():
        print(f'{status:<14}{n}')
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('photos', nargs='*', help='photo names given directly as arguments')
    parser.add_argument('--input', help='.txt/.csv/.json file listing the photos')
    parser.add_argument('--column', default='photo', help='column/key name (CSV/JSON), default "photo"')
    parser.add_argument('--output', default=DEFAULT_OUTPUT_DIR, help='destination folder')
    args = parser.parse_args()

    if args.photos:
        photos = args.photos
    elif args.input:
        photos = read_list(args.input, args.column)
    else:
        photos = PHOTOS  # default: hardcoded list at the top of the file

    download_photos(photos, args.output)


if __name__ == '__main__':
    main()
