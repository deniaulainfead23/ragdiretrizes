import os, re, sys, urllib.request, urllib.parse, zipfile, shutil
from pathlib import Path
from datetime import datetime

BASE = Path('/home/ubuntu/documentos/curriculos_computacao')
BASE.mkdir(parents=True, exist_ok=True)

items = [
    # Reino Unido
    ('reino-unido','reino-unido_computing-curriculum_ks1-ks2_2014.pdf','https://assets.publishing.service.gov.uk/media/5a7c576be5274a1b00423213/PRIMARY_national_curriculum_-_Computing.pdf','PDF oficial DfE/GOV.UK — National curriculum in England: computing KS1–2'),
    ('reino-unido','reino-unido_computing-curriculum_ks3-ks4_2014.pdf','https://assets.publishing.service.gov.uk/media/5a7cb981ed915d682236228d/SECONDARY_national_curriculum_-_Computing.pdf','PDF oficial DfE/GOV.UK — National curriculum in England: computing KS3–4'),

    # Irlanda
    ('irlanda','irlanda_computer-science-curriculum-specification_2018.pdf','https://www.curriculumonline.ie/getmedia/cff6eb86-9ff8-4e68-abf9-e42ca637492d/LC-Computer-Science-specification-updated.pdf','PDF oficial Curriculum Online/NCCA — Leaving Certificate Computer Science specification'),

    # Japão
    ('japao','japao_high-school-information-commentary_2022.pdf','https://www.mext.go.jp/content/1407073_11_1_2.pdf','PDF oficial MEXT — High School Course of Study commentary, Information'),
    ('japao','japao_high-school-curriculum-guidelines_2022.pdf','https://www.mext.go.jp/content/20220324-mxt_kouhou02-000021499_1.pdf','PDF oficial MEXT — High School Curriculum Guidelines'),

    # Singapura
    ('singapura','singapura_o-level-computing-syllabus_2021.pdf','https://www.moe.gov.sg/-/media/files/secondary/syllabuses/science/2021-o-level-computing-teaching-and-learning-syllabus.pdf','PDF oficial MOE Singapore — O-Level Computing syllabus; substitui o Computing Curriculum 2020 que parece restrito'),
    ('singapura','singapura_computer-applications-syllabus_archive-2019.pdf','https://www.moe.gov.sg/-/media/files/secondary/syllabuses/science/archive-2019-computer-applications-syllabus.pdf','PDF oficial MOE Singapore — Computer Applications syllabus'),

    # Taiwan
    ('taiwan','taiwan_technology-domain-information-technology_2019.pdf','https://www.k12ea.gov.tw/files/class_schema/%E8%AA%B2%E7%B6%B1/13-%E7%A7%91%E6%8A%80/13-1/%E5%8D%81%E4%BA%8C%E5%B9%B4%E5%9C%8B%E6%B0%91%E5%9F%BA%E6%9C%AC%E6%95%99%E8%82%B2%E8%AA%B2%E7%A8%8B%E7%B6%B1%E8%A6%81%E5%9C%8B%E6%B0%91%E4%B8%AD%E5%AD%B8%E6%9A%A8%E6%99%AE%E9%80%9A%E5%9E%8B%E9%AB%98%E7%B4%9A%E4%B8%AD%E7%AD%89%E5%AD%B8%E6%A0%A1%E2%94%80%E7%A7%91%E6%8A%80%E9%A0%98%E5%9F%9F.pdf','PDF oficial K-12 Education Administration/MOE Taiwan — 108課綱 Tecnologia, inclui 資訊科技'),

    # Coreia do Sul
    ('coreia-do-sul','coreia-do-sul_2015-revised-national-curriculum_moe-files.zip','https://www.moe.go.kr/boardCnts/fileDown.do?m=030201&s=moe&fileSeq=0d4b479163449e1164cb4a08256e8873','Arquivo oficial MOE Korea — pacote de arquivos do currículo 2015 revisado; pode conter HWP/PDF/ZIP'),
    ('coreia-do-sul','coreia-do-sul_keris-white-paper-software-education_2018.pdf','https://www.keris.or.kr/whitePaper/2018_study/keris_2018_eng_sample.pdf','PDF oficial KERIS — white paper com seção sobre implementação de software education no currículo 2015'),

    # Hong Kong
    ('hong-kong','hong-kong_ict-curriculum-and-assessment-guide_2017.pdf','https://www.edb.gov.hk/attachment/en/curriculum-development/kla/technology-edu/curriculum-doc/ICT_C&A_Guide_e_final.pdf','PDF oficial Education Bureau Hong Kong — ICT Curriculum and Assessment Guide'),
    ('hong-kong','hong-kong_general-studies-curriculum-guide_coding-stem_2017.pdf','https://www.edb.gov.hk/attachment/en/curriculum-development/cross-kla-studies/gs-primary/GSCG_2017_Eng.pdf','PDF oficial EDB Hong Kong — General Studies Guide 2017, inclui STEM/coding/computational thinking'),

    # Estônia
    ('estonia','estonia_digital-competence-model_2016.pdf','https://www.hm.ee/sites/default/files/digipadevuse_mudel_2016veebiuus.pdf','PDF oficial Ministério da Educação/Estônia — modelo de competência digital; substitui 2014 quando PDF específico não foi localizado'),

    # Finlândia
    ('finlandia','finlandia_new-national-core-curriculum-basic-education_2016.pdf','https://www.oph.fi/sites/default/files/documents/new-national-core-curriculum-for-basic-education.pdf','PDF oficial Finnish National Agency for Education — síntese do currículo 2016, inclui ICT competence/programming'),

    # Canadá
    ('canada','canada_ontario_digital-action-plan.pdf','https://files.ontario.ca/books/digital_action_plan.pdf','PDF oficial Ontario — Digital Action Plan; não é currículo específico de computação, mas documento oficial de estratégia digital'),
    ('canada','canada_ontario_ministry-education-published-plan_2023-2024.pdf','https://www.ontario.ca/page/published-plans-and-annual-reports-2023-2024-ministry-education','Página oficial Ontario — plano anual Educação 2023-2024; será salvo como HTML se não houver PDF direto'),
    ('canada','canada_alberta_k6-science-curriculum-computer-science_2023.pdf','https://open.alberta.ca/dataset/da982352-b50d-49a2-8805-c9073a7f5c5a63/resource/8322b928-cdfa-43c4-92bd-9e0a7f5c5a63/download/educ-new-curr-k6-science.pdf','PDF oficial Alberta — K-6 Science curriculum, inclui computer science'),
    ('canada','canada_alberta_draft-k6-science-update_2022.pdf','https://open.alberta.ca/dataset/9f8e10af-7ae8-466e-857f-09204b101454/resource/29edb210-0a9f-4f1f-b0f0-60fe092b3a11/download/edc-draft-curr-k6-science-update-2022-05.pdf','PDF oficial Alberta — draft K-6 Science update 2022, inclui computer science'),

    # EUA
    ('eua','eua_k12-computer-science-framework_2016.pdf','https://k12cs.org/wp-content/uploads/2016/09/K%E2%80%9312-Computer-Science-Framework.pdf','PDF oficial K–12 CS Framework'),

    # Chile
    ('chile','chile_tecnologia_programa_3-basico.pdf','https://www.curriculumnacional.cl/614/articles-20732_programa.pdf','PDF oficial Curriculum Nacional/MINEDUC — Tecnologia, 3º básico'),
    ('chile','chile_tecnologia_programa_4-basico.pdf','https://www.curriculumnacional.cl/614/articles-20733_programa.pdf','PDF oficial Curriculum Nacional/MINEDUC — Tecnologia, 4º básico'),
    ('chile','chile_tecnologia_programa_5-basico.pdf','https://www.curriculumnacional.cl/614/articles-20734_programa.pdf','PDF oficial Curriculum Nacional/MINEDUC — Tecnologia, 5º básico'),
    ('chile','chile_tecnologia_programa_6-basico.pdf','https://www.curriculumnacional.cl/614/articles-20735_programa.pdf','PDF oficial Curriculum Nacional/MINEDUC — Tecnologia, 6º básico'),
    ('chile','chile_bases-curriculares_educacion-basica_2012.pdf','https://www.curriculumnacional.cl/614/articles-346789_recurso_pdf.pdf','PDF oficial Curriculum Nacional/MINEDUC — Bases Curriculares Educação Básica, referência para tecnologia/informática'),

    # Uruguai
    ('uruguai','uruguai_plan-ceibal-in-uruguay.pdf','https://www.anep.edu.uy/sites/default/files/images/Archivos/publicaciones/plan-ceibal/plan%20ceibal%20in%20uruguay.pdf','PDF oficial ANEP — Plan CEIBAL in Uruguay'),
    ('uruguai','uruguai_en-el-camino-del-plan-ceibal_2009.pdf','https://www.anep.edu.uy/sites/default/files/images/Archivos/publicaciones/plan-ceibal/en%20el%20camino%20del%20plan%20ceibal%20-%202009.pdf','PDF oficial ANEP — En el camino del Plan CEIBAL'),
    ('uruguai','uruguai_tecnologias-digitales_2023.pdf','https://www.anep.edu.uy/sites/default/files/images/Archivos/programas-ems/finales/tab-1/Tecnolog%C3%ADas%20digitales%20-%20DGETP.v3.pdf','PDF oficial ANEP — Tecnologías digitales EMS; substituição curricular atual'),

    # Brasil
    ('brasil','brasil_bncc-computacao_anexo-parecer-cneceb-2-2022.pdf','https://basenacionalcomum.mec.gov.br/images/historico/anexo_parecer_cneceb_n_2_2022_bncc_computacao.pdf','PDF oficial MEC/BNCC — Computação na Educação Básica, complemento à BNCC'),
    ('brasil','brasil_bncc_educacao-infantil-ensino-fundamental_2017.pdf','https://basenacionalcomum.mec.gov.br/images/BNCC_20dez_site.pdf','PDF oficial MEC — BNCC 2017'),
    ('brasil','brasil_resolucao-cne-cp-2_2017.pdf','https://basenacionalcomum.mec.gov.br/images/historico/RESOLUCAOCNE_CP222DEDEZEMBRODE2017.pdf','PDF oficial MEC — Resolução CNE/CP nº 2/2017'),

    # Austrália
    ('australia','australia_digital-technologies-v9_sequence-content_2022.pdf','https://v8.australiancurriculum.edu.au/media/7510/v9-f-10-sequence-of-content-digital-technologies.pdf','PDF oficial Australian Curriculum/ACARA — v9 F–10 Digital Technologies sequence of content'),
    ('australia','australia_digital-technologies-v9_sequence-achievement_2022.pdf','https://v8.australiancurriculum.edu.au/media/7511/v9-f-10-digital-technologies-sequence-of-acheivement.pdf','PDF oficial Australian Curriculum/ACARA — v9 F–10 Digital Technologies achievement sequence'),

    # Nova Zelândia
    ('nova-zelandia','nova-zelandia_dt-implementation-support-tool_2020.pdf','https://storage.googleapis.com/media.dthm4kaiako.ac.nz/resources/100/DT_implementation_support_tool_2020.pdf','PDF oficial/suporte NZ Ministry of Education/TKI — Digital Technologies implementation support 2020'),
    ('nova-zelandia','nova-zelandia_now-underway-dt-implementation_2020.pdf','https://technologyonline.tki.org.nz/content/download/38601/196869/file/Now%20underway%20DT%20implementation.pdf','PDF oficial Technology Online/TKI — Now underway DT implementation support'),

    # África do Sul
    ('africa-do-sul','africa-do-sul_caps_computer-applications-technology_grades-10-12.pdf','https://www.education.gov.za/LinkClick.aspx?fileticket=ncRLjcM3K7Q%3D&tabid=2030&portalid=0&mid=7875&forcedownload=true','PDF oficial DBE South Africa — CAPS Computer Applications Technology Grades 10–12'),
    ('africa-do-sul','africa-do-sul_caps_information-technology_grades-10-12.pdf','https://www.education.gov.za/Portals/0/Documents/Publications/CAPS%20Commnets/FET/INFORMATION%20TECHNOLOGY%20GRADES%2010%20-%2012%20EDITED.PDF?ver=2018-08-29-154512-793','PDF oficial DBE South Africa — CAPS Information Technology Grades 10–12'),

    # Quênia
    ('quenia','quenia_basic-education-curriculum-framework_2017.pdf','https://kicd.ac.ke/wp-content/uploads/2017/10/CURRICULUMFRAMEWORK.pdf','PDF oficial KICD — Basic Education Curriculum Framework 2017, inclui digital literacy'),
    ('quenia','quenia_standards-digital-content-course-materials_cbc_2018.pdf','https://kicd.ac.ke/wp-content/uploads/2018/05/STANDARDS-FOR-DIGITAL-CONTENT-COURSE-MATERIALS_CBC-2018-Revised.pdf','PDF oficial KICD — Standards for Digital Content/Course Materials'),

    # Ruanda
    ('ruanda','ruanda_ict-syllabus.pdf','https://elearning.reb.rw/pluginfile.php/15466/mod_folder/content/0/ICT%20SYLLABUS.pdf?forcedownload=1','PDF oficial REB e-learning — ICT Syllabus'),

    # Gana
    ('gana','gana_computing-common-core-programme-curriculum_2023.pdf','https://nacca.gov.gh/wp-content/uploads/2023/06/COMPUTING.pdf','PDF oficial NaCCA Ghana — Computing Common Core Programme curriculum'),
    ('gana','gana_computing-primary-b4-b6_2019.pdf','https://nacca.gov.gh/wp-content/uploads/2019/04/COMPUTING-B4-B6.pdf','PDF oficial NaCCA Ghana — Computing B4–B6'),
]

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) curriculum-archive/1.0'}

def write_unavailable(country, filename, note):
    folder = BASE / country
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_text(note + '\n', encoding='utf-8')
    return path, 'INDISPONIVEL', len(note.encode('utf-8'))

def download(country, filename, url, note):
    folder = BASE / country
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    if url is None:
        return write_unavailable(country, filename, note)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
            ctype = r.headers.get('content-type','')
        # Ajuste se uma página HTML foi salva com extensão pdf
        if data[:5].lower().startswith(b'<html') or b'<!DOCTYPE html' in data[:200].upper():
            if path.suffix.lower() == '.pdf':
                path = path.with_suffix('.html')
        path.write_bytes(data)
        status = 'OK'
        if path.suffix.lower() == '.pdf' and not data.startswith(b'%PDF'):
            status = 'BAIXADO_MAS_VERIFICAR_FORMATO'
        if path.suffix.lower() == '.zip' and not data.startswith(b'PK'):
            status = 'BAIXADO_MAS_VERIFICAR_FORMATO'
        return path, status, len(data)
    except Exception as e:
        failname = re.sub(r'\.pdf$|\.zip$|\.html$', '_FALHA_DOWNLOAD.txt', filename)
        failpath = folder / failname
        failpath.write_text(f'Falha ao baixar de fonte oficial.\nURL: {url}\nErro: {e}\nObservação: {note}\n', encoding='utf-8')
        return failpath, 'FALHA_DOWNLOAD', failpath.stat().st_size

from concurrent.futures import ThreadPoolExecutor, as_completed

# Redefine a função de download com timeout menor e reaproveitamento de arquivos já baixados.
def download_fast(country, filename, url, note):
    folder = BASE / country
    folder.mkdir(parents=True, exist_ok=True)
    planned = folder / filename
    if url is None:
        if planned.exists():
            return planned, 'INDISPONIVEL', planned.stat().st_size
        return write_unavailable(country, filename, note)
    if planned.exists() and planned.stat().st_size > 1000:
        return planned, 'OK_EXISTENTE', planned.stat().st_size
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = r.read()
        path = planned
        head = data[:300].lstrip().lower()
        if (head.startswith(b'<html') or head.startswith(b'<!doctype html')) and path.suffix.lower() == '.pdf':
            path = path.with_suffix('.html')
        path.write_bytes(data)
        status = 'OK'
        if path.suffix.lower() == '.pdf' and not data.startswith(b'%PDF'):
            status = 'BAIXADO_MAS_VERIFICAR_FORMATO'
        if path.suffix.lower() == '.zip' and not data.startswith(b'PK'):
            status = 'BAIXADO_MAS_VERIFICAR_FORMATO'
        return path, status, len(data)
    except Exception as e:
        failname = re.sub(r'\.pdf$|\.zip$|\.html$', '_FALHA_DOWNLOAD.txt', filename)
        failpath = folder / failname
        failpath.write_text(f'Falha ao baixar de fonte oficial.\nURL: {url}\nErro: {e}\nObservação: {note}\n', encoding='utf-8')
        return failpath, 'FALHA_DOWNLOAD', failpath.stat().st_size

rows = []
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(download_fast, country, filename, url, note): (country, filename, url, note) for country, filename, url, note in items}
    for fut in as_completed(futs):
        country, filename, url, note = futs[fut]
        try:
            path, status, size = fut.result()
        except Exception as e:
            folder = BASE / country
            folder.mkdir(parents=True, exist_ok=True)
            failpath = folder / (filename + '_ERRO_EXECUCAO.txt')
            failpath.write_text(str(e), encoding='utf-8')
            path, status, size = failpath, 'ERRO_EXECUCAO', failpath.stat().st_size
        rows.append((country, path.name, status, size, url or '', note))

rows.sort(key=lambda x: (x[0], x[1]))
manifest = BASE / 'MANIFESTO.md'
with manifest.open('w', encoding='utf-8') as f:
    f.write('# Manifesto dos documentos curriculares de Computação\n\n')
    f.write(f'Gerado em: {datetime.utcnow().isoformat()}Z\n\n')
    f.write('Os arquivos foram organizados em subpastas por país. Status `OK`/`OK_EXISTENTE` indica download concluído; `INDISPONIVEL` indica ausência de PDF oficial público localizado; `FALHA_DOWNLOAD` indica que a URL oficial foi identificada, mas o servidor não permitiu/retornou erro nesta execução.\n\n')
    f.write('| País | Arquivo | Status | Tamanho | Fonte/observação |\n')
    f.write('|---|---|---:|---:|---|\n')
    for country, name, status, size, url, note in rows:
        src = (url + ' — ' if url else '') + note
        src = src.replace('|','\\|')
        f.write(f'| {country} | `{country}/{name}` | {status} | {size} | {src} |\n')

print(f'Concluído. Manifesto: {manifest}')
for r in rows:
    print('\t'.join(map(str,r[:4])))
