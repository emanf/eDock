from dataclasses import dataclass ,field 
from typing import Any ,Optional ,Dict ,List 


@dataclass 
class Package :

    id :str 
    title :str 
    version :Optional [str ]=None 
    description :Optional [str ]=None 
    author :Optional [str ]=None 
    manifest_url :Optional [str ]=None 
    download_url :Optional [str ]=None 
    icon :Optional [str ]=None 
    category :Optional [str ]=None 
    keywords :Optional [List [str ]]=None 
    homepage :Optional [str ]=None 
    min_dock_version :Optional [str ]=None 
    sha256 :Optional [str ]=None 


    metadata :Dict [str ,Any ]=field (default_factory =dict )

    def to_dict (self )->Dict [str ,Any ]:
        return {
        "id":self .id ,
        "title":self .title ,
        "version":self .version ,
        "description":self .description ,
        "author":self .author ,
        "manifest_url":self .manifest_url ,
        "download_url":self .download_url ,
        "icon":self .icon ,
        "category":self .category ,
        "keywords":self .keywords ,
        "homepage":self .homepage ,
        "min_dock_version":self .min_dock_version ,
        "sha256":self .sha256 ,
        **self .metadata ,
        }

    @classmethod 
    def from_dict (cls ,data :Dict [str ,Any ])->"Package":
        metadata ={k :v for k ,v in data .items ()
        if k not in ("id","title","version","description","author",
        "manifest_url","download_url","icon","category",
        "keywords","homepage","min_dock_version","sha256")}

        return cls (
        id =data .get ("id",""),
        title =data .get ("title",data .get ("name","")),
        version =data .get ("version"),
        description =data .get ("description"),
        author =data .get ("author"),
        manifest_url =data .get ("manifest_url")or data .get ("manifest")or data .get ("app_manifest"),
        download_url =data .get ("download_url")or data .get ("download")or data .get ("install_url"),
        icon =data .get ("icon"),
        category =data .get ("category"),
        keywords =data .get ("keywords"),
        homepage =data .get ("homepage"),
        min_dock_version =data .get ("minDockVersion")or data .get ("min_dock_version"),
        sha256 =data .get ("sha256"),
        metadata =metadata ,
        )
