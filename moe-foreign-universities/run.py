"""
[x]1. 主页解析：国家链接
[x]2. 新版格式解析
[ ]3. 旧版格式解析：部分为段落/列表格式，部分为表格形式，部分页面有子链接
"""
import json
import os

import re
import requests

from bs4 import BeautifulSoup
from bs4.element import Tag


def parse_index(html_file):
    """首页解析"""
    soup = BeautifulSoup(open(html_file), 'html.parser')
    # text = soup.prettify()
    part_body = soup.body
    part_article = part_body.find_all(name='div', attrs={"class": "article left"})
    assert len(part_article) == 1
    part_article = part_article[0]

    out_title = part_article.h1.text
    out_datetime = part_article.find(id="datetime").text.strip()  # 更新时间信息
    # title = outx.h1.text
    # time = outx.h4.text.strip()

    part_school = part_article.find(id="Zoom").find_all(name="div", class_="school")[0]
    part_sclist = part_school.find_all(name="div", class_="scList")  # 若干行，每个单元格一个国家链接

    # 国家名
    all_style_list = []
    new_style_list = []
    # {国家: 链接}
    href_dict = {}
    for sc in part_sclist:
        for li in sc.ul.contents:
            a = li.a
            if a is None: continue
            href = a.attrs.get('href')
            name = a.text.strip()
            if href == "*" or len(name) == 0: continue
            if name.startswith("*"):
                name = name.strip("*").strip()
                new_style_list.append(name)
            all_style_list.append(name)
            href_dict[name] = href

    return out_title, out_datetime, all_style_list, new_style_list, href_dict


def parse_new_styles(html_file):
    soup = BeautifulSoup(open(html_file), 'html.parser')

    part_body = soup.body
    out = part_body.find_all("div", class_="gwBox")
    assert len(out) == 1
    out = out[0]

    parts = out.contents
    assert len(parts) in [2, 3]  # 3个div：标题、时间和内容（高等教育体制简介、名单）
    name = parts[0].h1.text  # class="tit_gw"
    if len(parts) == 3:
        time = parts[1].text  # style="xx"
    else:
        time = None

    # 正文解析
    main_part = parts[-1]  # class="gwCon"
    gwlist = main_part.find_all("div", class_="gw")  # len(gwlist) == 2; 高等教育体制简介、名单

    # 高等教育体制简介
    gw0 = gwlist[0]
    assert gw0.attrs['class'][0] == 'gw'
    gw_parts = gw0.find_all("div")
    # assert  len(gw_parts) == 2, len(gw_parts) # todo 丹麦

    gw0_title = gw_parts[0]
    ## 标题
    assert gw0_title.attrs['class'][0] == "tit2"
    title = gw0_title.h2.text
    assert title == '高等教育体制简介'

    gw0_para = gw_parts[1]
    ## 正文
    assert gw0_para.attrs['class'][0] == "gwTxt"
    plist = gw0_para.find_all("p")
    main_info = [p.text.strip() for p in plist]

    # 学校名单
    gw1 = gwlist[1]
    assert gw1.attrs['class'][0] == 'gw'

    gw1_parts = gw1.contents
    gw1_title = gw1.find_all("div", class_='tit2')
    gw1_paras = gw1.find_all("div", class_="gwList")

    gw1_parts = [p for p in gw1_parts if isinstance(p, Tag) and p.name == 'div']
    sc_details = {}
    sc_types = []
    current = ""  # 可能没有
    for i, g in enumerate(gw1_parts):
        attrs = g.attrs
        if i == 0 or ('class' in attrs and attrs.get('class')[0] == 'tit2'):
            continue

        elif attrs.get("style") is not None:
            sc_type = g.text

            sc_types.append(sc_type)
            sc_details[sc_type] = []
            current = sc_type
            # print(current)
            continue
        elif 'class' in attrs and attrs.get("class")[0] == 'gwList':
            sc_info = []
            for child in g.children:
                assert child.name == 'p'
                # out = child.text.split("：")
                sc_info.append(child.text)
            # assert current is not None
            if current not in sc_details:
                sc_details[current] = []
            sc_details[current].append(sc_info)

    return name, time, main_info, sc_types, sc_details


def parse_old_styles(html_file, sub=False):
    ## 旧版解析 v1
    soup = BeautifulSoup(open(html_file), "html.parser")
    part_body = soup.body

    # 这是新版
    out = part_body.find_all("div", class_="gwBox")
    assert len(out) == 0

    # 这是旧版
    out = part_body.find_all("div", class_="list left")
    assert len(out) == 1
    out = out[0].find("div", class_="article left")

    xpart = [part for part in out.contents if isinstance(part, Tag)]  # 去除没有标签的文本，如'\n'
    name = xpart[0].text.strip()  # h1
    time = xpart[1].text.strip()  # h4

    # 正文解析：基本情况、名单
    main_part = xpart[2]
    assert main_part.attrs['id'] == "Zoom"  # class="article-nr left" id="Zoom"

    # 只有<p>、<table>/<blockquote>
    for e in main_part.find_all("br"):
        e.extract()
    plist = [p for p in main_part.contents if isinstance(p, Tag)]

    gw0 = []  # 简介/基本情况
    gw1 = []  # 名单
    part_id = -1
    mode = 1
    for i, para in enumerate(plist):
        if (para.name == 'p' and part_id < 1 and para.strong is not None):
            text = para.strong.text.strip()
            if '基本情况' in text:
                part_id = 0

            elif '名单' in text:
                part_id = 1

        if para.name in ['table', 'blockquote'] and part_id == 0:
            part_id = 1
            # print("="*10, name)
            mode += 1000
        if part_id == 0:
            gw0.append(para)
        elif part_id == 1:
            gw1.append(para)

    print(name, len(gw0), len(gw1))

    # if name in ['俄罗斯',  ]: return
    print(html_file)
    assert len(gw0) >= 0 and len(gw1) > 0
    # assert
    for x in gw1:
        if x.name in ['table']:
            mode += 100
        if x.name in ['blockquote']:
            mode += 10

    if mode // 100 % 10 > 0:  # 表格
        print(name)

    # 第一部分解析
    main_info = parse_old_part1(gw0)
    assert (len(gw0) > 0 and len(out) > 0) or (len(gw0) == 0)  # or name in ['俄罗斯']

    # 第二部分解析
    # 1形状
    sc_types, sc_details = parse_old_part2a(gw1)
    # print(len(sc_types), sc_types)
    # print(sc_details)
    return mode, name, time, main_info, sc_types, sc_details


def parse_old_part1(gw0):
    """'列支敦士登' 没有基本信息"""
    out = []
    main_info = []  # [p.text.strip() for p in plist]
    has_title = False
    for entry in gw0:
        assert entry.name == 'p'

        if len(entry.contents) and entry.contents[0].name == 'span':  # 俄罗斯
            entry = entry.span
        for line in entry.contents:
            if isinstance(line, Tag):
                if line.name == 'strong':
                    text = line.text.strip()
                    if '基本情况' in text:
                        has_title = True
                        continue
                    else:
                        print(line)
                else:
                    text = line.text.strip()

            else:
                text = line.strip()
            if has_title:
                if len(text) == 0 or '-分类目录-' in text: continue  # 日本/加拿大
                main_info.append(text)

    return main_info


def parse_old_part2a(gw1):
    # 表格链接子页面
    part_table = []
    for entry in gw1:
        if entry.name == 'table':
            part_table.append(entry)
    assert len(part_table) == 1
    part_table = part_table[0]
    tdlist = part_table.find_all("td")
    # print(para.find_all("a"))
    sc_details = {}
    sc_types = []
    tdlist2 = [td for td in tdlist if td.a is not None]
    for td in tdlist2:
        href = td.a.attrs['href']
        name = td.a.text.strip()
        sc_types.append(name)
        sc_details[name] = href
    return sc_types, sc_details


def parse_old_styles_sub(html_file):
    ## 旧版解析 v1- 子子页面
    soup = BeautifulSoup(open(html_file), "html.parser")
    part_body = soup.body

    # 这是新版
    out = part_body.find_all("div", class_="gwBox")
    assert len(out) == 0

    # 这是旧版
    out = part_body.find_all("div", class_="list left")
    assert len(out) == 1
    out = out[0].find("div", class_="article left")

    xpart = [part for part in out.contents if isinstance(part, Tag)]
    assert len(xpart) == 3
    title = xpart[0].text  # h1
    main_part = xpart[2]
    assert main_part.attrs['id'] == "Zoom"  # class="article-nr left" id="Zoom"
    gw = [part for part in main_part.contents if isinstance(part, Tag)]

    # 韩国
    gw1 = main_part.find("table")
    if gw1 is not None:
        title2, sclist = parse_old_part_table(gw1)
        print(title2, len(sclist))
    else:
        title2, sclist = "", []

    # assert len(out2) == 1
    # # out3 = [part for part in out2[0][-1].contents if isinstance(part, Tag)]
    # start=False

    # for entry in out2[0].contents:
    #     if isinstance(entry, Tag) and entry.strong is not None:
    #         title2 = entry.text.strip()
    #         start=True
    #         continue
    #     if start and not isinstance(entry, Tag):
    #         text = entry.strip()
    #         if len(text) > 0:
    #             sclist.append(text)
    #
    return title, {title2: sclist}


def parse_old_part_table(gw1):
    """
    日本 存在格式不一致；一个学院多行
    瑞士：一个学校下设系
    :param gw1:
    :return:
    """
    title2 = ""
    sclist = []
    assert gw1.name == 'table'
    tlist = gw1.tbody.contents  # tr
    caption = [t.text.strip() for t in tlist[0].contents]  # td
    # 存在列数不一致导致使用多行的情况

    # for i in range(1, len(tlist)):
    N = len(tlist)
    i = 1
    temp = []
    while i < N:
        entry = tlist[i]
        i += 1
        values = [t.text.strip() for t in entry.contents]
        if len(values) == len(caption) > 0:
            sclist.append(dict(zip(caption, values)))
            if len(temp) > 0:
                # todo 连续合并有问题：中间隔断
                sclist.append(temp)
                temp = []
        elif len(values) == 1:
            temp.append(values[0])
        if i == N and len(temp) > 0:
            sclist.append(temp)

    # while i < N:
    #     entry = tlist[i]
    #     i += 1
    #     values = [t.text.strip() for t in entry.contents]
    #     if len(values) == len(caption):
    #         sclist.append(dict(zip(caption, values)))
    #
    #     else:
    #         temp = values
    #         while i < N:
    #             entry = tlist[i]
    #             values = [t.text.strip() for t in entry.contents]
    #             if len(values) == len(caption): break
    #             temp.extend(values)
    #             i += 1
    #         sclist.append(temp)
    return title2, sclist


def run_index(data_base, data_dir, info_file):
    base_host = "http://jsj.moe.gov.cn"
    main_href = "/n1/12018.shtml"
    main_url = base_host + main_href

    # 首页
    post_name = "-".format(["main"] + re.split("[/.]", main_href)[1:3])
    save_file_main = "{}/{}.html".format(data_base, post_name)
    save_file_main2 = "{}/{}-pretty.html".format(data_base, post_name)

    result = requests.get(main_url)
    text = result.text.encode(result.encoding).decode('utf-8')
    with open(save_file_main, "w", encoding='utf-8') as fw:
        fw.write(text)

    out_title, out_datetime, all_style_list, new_style_list, href_dict = parse_index(save_file_main)
    # 国家子页面（链接）
    for name, href in href_dict.items():
        url = base_host + href
        response = requests.get(url)
        if response.status_code != 200:
            print("Error: {} {}".format(name, url))
            continue

        text = response.text.encode(response.encoding).decode('utf-8')
        # post_name = href.split("/")[-1]
        post_name = "-".format([name] + re.split("[/.]", href)[1:3])
        save_file_sub = "{}/{}.html".format(data_dir, post_name)
        with open(save_file_sub, "w", encoding='utf-8') as fw:
            fw.write(text)

    new_style_list += ['芬兰', '拉脱维亚']
    old_style2_list = ['美国', '韩国', '澳大利亚', '加拿大', '日本', '瑞士']  # 正文页面没有大学，只有链接

    # 保存信息
    out_info = {
        "title": out_title,
        "datetime": out_datetime,
        "website": base_host,
        "main": main_href,
        "country-href": href_dict,
        "all": all_style_list,
        "new": new_style_list,
        "old2": old_style2_list
    }

    with open(info_file, "w", encoding="utf-8") as fw:
        json.dump(out_info, fw, indent=2, ensure_ascii=False)


def run_new(data_dir, save_dir, info_file):
    os.makedirs(save_dir, exist_ok=True)
    data = json.load(open(info_file))
    href_dict = data['place-href']
    new_style_list = data['places-update']
    new_style_list += ['芬兰', '拉脱维亚']

    for i, country_name in enumerate(new_style_list):
        href = href_dict[country_name]
        # if not name == '以色列': continue
        full_name = "{}-{}".format(country_name, href.split("/")[-1])
        save_file = "{}/{}.json".format(save_dir, full_name.split(".")[0])
        html_file = "{}/{}".format(data_dir, full_name)
        print("{}/{}: {}, {}, {}".format(i, len(new_style_list), country_name, href, full_name))

        title_name, update_datetime, main_info, sc_types, sc_details = \
            parse_new_styles(html_file)

        save_data = {
            "name": country_name,
            "title": title_name,
            "time": update_datetime,
            "main_info": main_info,
            "school_types": sc_types,
            "school_list": sc_details
        }
        with open(save_file, "w", encoding="utf-8") as fw:
            json.dump(save_data, fw, ensure_ascii=False, indent=2)


def run_old(data_dir, save_dir, info_file):
    os.makedirs(save_dir, exist_ok=True)
    data = json.load(open(info_file))

    href_dict = data['place-href']
    all_style_list = data['places']
    new_style_list = data['places-update']
    new_style_list += ['芬兰', '拉脱维亚']
    old_style2_list = ['美国', '韩国', '澳大利亚', '加拿大', '日本', '瑞士']

    mode_dict = {}
    for i, country_name in enumerate(all_style_list):
        if country_name in new_style_list: continue
        if country_name not in old_style2_list: continue

        href = href_dict[country_name]
        # if name != '乌克兰': continue

        full_name = "{}-{}".format(country_name, href.split("/")[-1])
        save_file = "{}/{}.json".format(save_dir, full_name.split(".")[0])
        html_file = "{}/{}".format(data_dir, full_name)
        # print("{}/{}: {}, {}, {}".format(i, len(new_style_list), country_name, href, full_name))
        mode, title_name, update_datetime, main_info, sc_types, sc_details = \
            parse_old_styles(html_file)
        sc_types, sc_details = [], []
        if mode not in mode_dict:
            mode_dict[mode] = []
        mode_dict[mode].append(country_name)

        if country_name in old_style2_list:
            info2 = {
                "name": country_name,
                "school_types": sc_types,
                "school_list": sc_details
            }
            # todo save

        save_data = {
            "name": country_name,
            "title": title_name,
            "time": update_datetime,
            "main_info": main_info,
            "school_types": sc_types,
            "school_list": sc_details
        }
        with open(save_file, "w", encoding="utf-8") as fw:
            json.dump(save_data, fw, ensure_ascii=False, indent=2)


def run_old_sub(data_dir):
    country_list = os.listdir(data_dir)
    # country_list = ['美国']
    # country_list = ['韩国']
    for name in sorted(country_list):
        print(name)
        if name in ['美国', '澳大利亚', '加拿大']: continue
        files = os.listdir("{}/{}".format(data_dir, name))
        for f in sorted(files):
            # print("\t{}".format(f))
            html_file = "{}/{}/{}".format(data_dir, name, f)
            print("\t", html_file)
            parse_old_styles_sub(html_file)


if __name__ == '__main__':
    data_base = "htmls"
    data_dir = "htmls/sub"
    data_dir2 = "htmls/sub2"
    info_file = "htmls/info.json"

    save_dir = "results/result-new"
    save_dir2 = "results/result-old"

    run_index(data_base, data_dir, info_file)
    run_new(data_dir, save_dir, info_file)
    run_old(data_dir, save_dir2, info_file)
    run_old_sub(data_dir2)
