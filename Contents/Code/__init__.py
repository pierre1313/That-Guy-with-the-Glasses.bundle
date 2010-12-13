import re

TGWTG_PREFIX                   = '/video/thatguywiththeglasses'
TGWTG_URL                      = 'http://thatguywiththeglasses.com'
IMAGE_BASEURL                  = "http://a.images.blip.tv/"
BLIP_API                       = "http://blip.tv/player/episode/%s?skin=json&version=2&callback="
BLIP_SEARCH_API                = "http://www.blip.tv/search/view/?search=%s&skin=json&version=2&callback="
BLIP_CATEGORY_API              = "http://www.blip.tv/%s?skin=json&version=2&callback="

DEBUG                         = True
CACHE_FRONTPAGE               = 64000 
CACHE_SHOWPAGE                = CACHE_FRONTPAGE
CACHE_RSS                     = 3200
CACHE_EPISODE_RSS             = 640000 # This contains just one show so we can cache for ages

RSS_NAMESPACE                  = {'media':'http://search.yahoo.com/mrss/', 'blip':'http://blip.tv/dtd/blip/1.0'}

ART = 'art-default.png'
ICON = 'icon-default.png'
SEARCH = 'icon-search.png'

####################################################################################################

def Start():
  Plugin.AddPrefixHandler(TGWTG_PREFIX, ShowSelector, L('tgwtg'), ICON, ART)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('Details', viewMode='InfoList', mediaType='items')
  MediaContainer.content = 'Items'
  MediaContainer.art = R(ART)
  MediaContainer.viewGroup = 'List'
  MediaContainer.title1 = L('tgwtg')
  DirectoryItem.thumb = R(ICON)
  HTTP.CacheTime = 3600

def UpdateCache():

  HTTP.Request(TGWTG_URL, cacheTime=CACHE_FRONTPAGE).content

def ShowSelector(sender=None, parentID='', title1=L('tgwtg'), title2=''):
  dir = MediaContainer()

  page = HTML.ElementFromURL(TGWTG_URL, cacheTime=CACHE_FRONTPAGE)
  
  if(parentID == ''):
  	parent = page.xpath("//ul[@class='menutop']")[0]
	children = parent.xpath("./li")

  else:
	parent = page.xpath("//li[contains(@class, '"+parentID+"')]")[0]
	children = parent.xpath("./div/ul/li")

  for child in children:
    url = TGWTG_URL + child.xpath("./a")[0].get('href')
    title = child.xpath("./a/span")[0].text
    # Update : Some child can be skipped (no videos) for the root element. Not very clean, feel free to correct with a better way
    if(title == 'Articles' or title == 'Home' or title == 'Site Stuff' or title == 'Store' or title == 'Community'):
	    continue
    liClass = child.get('class')
    # If the child's class contains 'parent' then it has it's own children
    if liClass.count('parent') > 0:
      # Is a parent, extract the item
      #Update: $ removed, the class is at the start now
      childID = re.search(r'(item\d+)', liClass).group(1)
      dir.Append(Function(DirectoryItem(ShowSelector, title=title, thumb=R(ICON)), parentID=childID, title1=title2, title2=title))
    else:
      # Is not a parent, is a show, so pass to ShowBrowser
      childId = liClass
      dir.Append(Function(DirectoryItem(ShowBrowser, title=title, thumb=R(ICON)), showUrl=url, order=title, title1=title2))
  
  if sender == None:
    for cat in ['popular', 'recent', 'random', 'featured']:
      dir.Append(Function(DirectoryItem(ShowCategoryNSearch,str(cat).capitalize(), str(cat).capitalize(), str(cat).capitalize(), thumb=R(ICON)),category = cat))
    dir.Append(Function(InputDirectoryItem(ShowCategoryNSearch,"Search...", "Search...", "Search...", thumb=R(SEARCH))))

  return dir

def ShowBrowser(sender, showUrl, order, title1):

  dir = MediaContainer(title1 = title1,title2 = L(order),viewGroup = 'Details')
  
  for episode in  HTML.ElementFromURL(showUrl).xpath("//tr[starts-with(@class,'sectiontableentry')]"):
	url = TGWTG_URL + episode.xpath("./td[position()=2]/a")[0].get('href')
	try :
	  blipid = HTML.ElementFromURL(url, cacheTime=CACHE_SHOWPAGE).xpath("//embed")[0].get('src')
	  blipid = (blipid[blipid.rfind('/')+1:]).replace('%2B','+').replace('%2D','-')
	except:
	  blipid = None
	  
	#Log(blipid)
	if blipid!=None:
  	  if len(blipid)>11:
	    blipid = blipid[:blipid.rfind('+')]
	
	  jsonresponse = HTTP.Request(BLIP_API%blipid).content.replace('([{','[{').replace(']);',']').replace("\'","'")
	  for episodeInfo in JSON.ObjectFromString(jsonresponse):
	    if "error" in episodeInfo:
	      Log("Error")
	    else:
	      url = episodeInfo['mediaUrl']
	      title = episodeInfo['title']
	      subtitle = episodeInfo['description']
	      summary = episodeInfo['description']
	      try:
	        thumb = episodeInfo['thumbnailUrl']
	      except:
	        thumb =''
  	      duration = int(episodeInfo['media']['duration'])*1000
	    
	      dir.Append(VideoItem(url, title=title, subtitle=subtitle, thumb=Function(GetThumb,url=thumb), summary=summary,duration = duration))
  return dir
  
def ShowCategoryNSearch(sender, query = None,category = None):
  
  dir = MediaContainer(viewGroup = 'Details')

  if query == None:
    jsonresponse = HTTP.Request(BLIP_CATEGORY_API%category).content.replace('([{','[{').replace(']);',']').replace("\'","'")
  else:
    jsonresponse = HTTP.Request(BLIP_SEARCH_API%query).content.replace('([{','[{').replace(']);',']').replace("\'","'")
  for episodeInfo in JSON.ObjectFromString(jsonresponse):
    if "error" in episodeInfo:
      Log("Error")
    else:
      url = episodeInfo['mediaUrl']
      title = episodeInfo['title']
      subtitle = episodeInfo['description']
      summary = episodeInfo['description']
      try:
        thumb = episodeInfo['thumbnailUrl']
      except:
        thumb =''
      duration = int(episodeInfo['media']['duration'])*1000
    
      dir.Append(VideoItem(url, title=title, subtitle=subtitle, thumb=Function(GetThumb,url=thumb), summary=summary,duration = duration))
  return dir
    
def GetThumb(url):
  try:
    return DataObject(HTTP.Request(url, cacheTime=CACHE_1WEEK), 'image/jpeg')
  except:
    return Redirect(R(ICON))
