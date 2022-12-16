import pandas as pd

class RecipeParseException(Exception):
    pass

class Recipe:
    def __init__(self, recipe_details=None, recipe_df=None, recipe_dict=None):
        if recipe_dict == None:
            self.set_recipe_details(recipe_details)
            self.set_recipe_df(recipe_df)
        else:
            self.set_recipe_dict(recipe_dict)

    def set_recipe_details(self, recipe_details):
        self.__recipe_details = recipe_details

    def set_recipe_df(self, recipe_df):
        self.__recipe_df = recipe_df

    def set_recipe_dict(self, recipe_dict):
        self.__recipe_df = pd.DataFrame(recipe_dict['recipe'], columns=['qty', 'unit', 'item'])
        del recipe_dict['recipe']
        self.__recipe_details = recipe_dict

    def get_recipe_details(self):
        return self.__recipe_details

    def get_recipe_df(self):
        return self.__recipe_df

    def get_recipe_dict(self):
        to_return = self.__recipe_details.copy()
        to_return['recipe'] = []
        for idx, row in self.__recipe_df.iterrows():
            to_return['recipe'].append(row.to_dict())
        return to_return
    
    def __dict_equality(self, dict1, dict2):
        for key in dict1:
            if key in dict2:
                if type(dict1[key]) == type(dict2[key]):
                    if type(dict1[key]) is dict:
                        if not self.__dict_equality(dict1[key], dict2[key]):
                            return False
                    else:
                        if dict1[key] != dict2[key]:
                            return False
                else:
                    return False
            else:
                return False
        return True
    
    def equals(self, other_recipe):
        self_recipe_dict = self.get_recipe_dict()
        other_recipe_dict = other_recipe.get_recipe_dict()
        
        return self.__dict_equality(self_recipe_dict, other_recipe_dict)