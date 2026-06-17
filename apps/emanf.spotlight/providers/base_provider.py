from abc import ABC ,abstractmethod 
from typing import List ,Dict ,Any 
from ..models import SearchResult 


class BaseProvider (ABC ):

    @abstractmethod 
    def search (self ,query :str )->List [SearchResult ]:
        pass 

    @abstractmethod 
    def get_name (self )->str :
        pass 
