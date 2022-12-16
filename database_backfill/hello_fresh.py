import time
import recipe
import requests
import unicodedata
import pandas as pd
from bs4 import BeautifulSoup

__base_url = 'https://www.hellofresh.com'

def __verbose_print(to_print, verbose):
    if verbose:
        print(to_print)

##### SECTION 1:  Finding all recipe links #####

def __get_all_links(soup, base_url):
    links = []
    for x in soup.find_all('a', href=True):
        if '/recipes' in x['href']:
            links.append(x['href'].replace(base_url, ''))
    return links

def __filter_links(links):
    other_links = []
    recipe_links = []
    for link in links:
        if link[-1] == '/':
            link = link[:-1]
        if '-' in link and len(link.split('-')[-1]) >= 20:
            recipe_links.append(link)
        else:
            other_links.append(link)
    return recipe_links, other_links

def find_recipe_urls(verbose=False):
    prev_extensions = []
    search_extensions = ['/recipes']
    recipe_extensions = []
    
    while len(search_extensions) > 0:
        curr_search_extension = search_extensions.pop(0)
        __verbose_print(str(len(search_extensions)) + '\t' + curr_search_extension, verbose)
        prev_extensions.append(curr_search_extension)
    
        search_url = __base_url + curr_search_extension
        search_page = requests.get(search_url)
        search_soup = BeautifulSoup(search_page.content, "html.parser")
        search_links = __get_all_links(search_soup, __base_url)
        
        recipe_links, other_links = __filter_links(search_links)
        
        recipe_extensions.extend(recipe_links)
        for link in other_links:
            if link not in prev_extensions and link not in search_extensions:
                search_extensions.append(link)

    to_return = list(set(recipe_extensions))
    for i in range(len(to_return)):
        to_return[i] = __base_url + to_return[i]
    return to_return

##### SECTION 2:  Parsing recipe links to recipe objects #####

def __get_recipe_soup(url):
    recipe_page = None
    
    retries = 0
    while retries < 10:
        try:
            recipe_page = requests.get(url)

            if recipe_page.status_code != 200:
                raise requests.exceptions.HTTPError
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
            pass
        retries += 1
        time.sleep(5*retries)
    
    recipe_soup = BeautifulSoup(recipe_page.content, "html.parser")

    return recipe_soup

def __parse_numeric(num_str):
    try:
        return float(num_str)
    except:
        if len(num_str) == 1:
            return unicodedata.numeric(num_str)
        else:
            return float(num_str[:-1]) + unicodedata.numeric(num_str[-1])

def __get_recipe_df(recipe_soup):
    recipe_elements = [x.text for x in recipe_soup.find_all('p')]
    
    while 'produced' not in recipe_elements[0].lower():
        recipe_elements = recipe_elements[1:]
    recipe_elements = recipe_elements[1:]
    while 'people' in recipe_elements[0]:
        recipe_elements = recipe_elements[1:]
    recipe_elements = [x.strip() for x in recipe_elements]
    recipe_elements = [x for x in recipe_elements if x != '']
    
    max_index = 0
    for i in range(len(recipe_elements)):
        if 'salt' == recipe_elements[i].lower().split(' ')[-1] or 'pepper' == recipe_elements[i].lower().split(' ')[-1]:
            max_index = i
            
    recipe_elements = recipe_elements[:max_index+1]
    
    recipe_dict_list = []
    new_item = {}
    for i in range(len(recipe_elements)):
        if any(char.isdigit() or char.isnumeric() for char in recipe_elements[i]):
            new_item['qty'] = ''
            new_item['unit'] = ''
            
            amount_elements = recipe_elements[i].split(' ')
            for element in amount_elements:
                if any(char.isdigit() or char.isnumeric() for char in element):
                    new_item['qty'] += element + ' '
                else:
                    new_item['unit'] += element + ' '
            
            new_item['qty'] = new_item['qty'][:-1]
            new_item['unit'] = new_item['unit'][:-1]
        else:
            new_item['item'] = recipe_elements[i]
            recipe_dict_list.append(new_item)
            new_item = {}
    
    df = pd.DataFrame(recipe_dict_list, columns=['qty', 'unit', 'item'])
    df = df[df.item != 'unit']
    df['qty'] = df['qty'].apply(__parse_numeric)
    df['item'] = df['item'].str.lower()
    df = df.fillna("")
    
    return df

def __rindex_val(x, elem, offset=0, exact=True):
    x_copy = [x_val.lower() for x_val in x]
    elem_copy = elem.lower()
    
    if exact:
        try:
            return x[len(x) - 1 - x_copy[::-1].index(elem_copy) + offset]
        except:
            return ""
    else:
        last_idx = None
        for i in range(len(x)):
            if elem_copy in x_copy[i]:
                last_idx = i
        if last_idx is not None:
            return x[last_idx + offset]
        return ""

def __get_recipe_details(recipe_soup, url):
    recipe_details = {}
    
    recipe_details['url'] = url
    recipe_details['name'] = recipe_soup.find_all("h1", {"data-test-id": "recipeDetailFragment.recipe-name"})[0].text
    recipe_details['description'] = recipe_soup.find_all("p")[0].text
    recipe_details['servings'] = 2
    
    all_spans = [span.text for span in recipe_soup.find_all("span")]
    recipe_details['allergens'] = {}
    recipe_details['allergens']['immediate'] = [x.lower() for x in __rindex_val(all_spans, 'Allergens', offset=1).split('•')]
    recipe_details['allergens']['secondary'] = [x.lower() for x in __rindex_val(all_spans, 'Produced in a facility that processes ', exact=False)[len('Produced in a facility that processes '):].replace('and ', '').replace('.', '').split(', ')]
    recipe_details['time'] = {}
    recipe_details['time']['total'] = __rindex_val(all_spans, 'Total Time', offset=1)
    recipe_details['time']['prep'] = __rindex_val(all_spans, 'Prep Time', offset=1)
    recipe_details['difficulty'] = __rindex_val(all_spans, 'Cooking difficulty', offset=1)
    recipe_details['difficulty'] = __rindex_val(all_spans, 'Cooking difficulty', offset=1)
    recipe_details['nutrition'] = {}
    recipe_details['nutrition']['calories'] = __rindex_val(all_spans, 'Calories', offset=1)
    recipe_details['nutrition']['fat'] = __rindex_val(all_spans, 'Fat', offset=1)
    recipe_details['nutrition']['saturated_fat'] = __rindex_val(all_spans, 'Saturated Fat', offset=1)
    recipe_details['nutrition']['carbohydrates'] = __rindex_val(all_spans, 'Carbohydrates', offset=1)
    recipe_details['nutrition']['sugar'] = __rindex_val(all_spans, 'Sugar', offset=1)
    recipe_details['nutrition']['fiber'] = __rindex_val(all_spans, 'Dietary Fiber', offset=1)
    recipe_details['nutrition']['protein'] = __rindex_val(all_spans, 'Protein', offset=1)
    recipe_details['nutrition']['cholesterol'] = __rindex_val(all_spans, 'Cholesterol', offset=1)
    recipe_details['nutrition']['sodium'] = __rindex_val(all_spans, 'Sodium', offset=1)
    
    return recipe_details

def get_recipe(url):
    recipe_soup = None
    try:
        recipe_soup = __get_recipe_soup(url)
    except:
        raise recipe.RecipeParseException('Invalid Recipe URL\n' + url)

    recipe_df = None
    try:
        recipe_df = __get_recipe_df(recipe_soup)
    except:
        raise recipe.RecipeParseException('Invalid Recipe URL\n' + url)

    for column in recipe_df.columns:
        if recipe_df[column].isnull().all():
            raise recipe.RecipeParseException('Invalid Recipe URL\n' + url)

    recipe_details = None
    try:
        recipe_details = __get_recipe_details(recipe_soup, url)
    except:
        raise recipe.RecipeParseException('Invalid Recipe URL\n' + url)

    to_return = recipe.Recipe(recipe_details, recipe_df)
    return to_return