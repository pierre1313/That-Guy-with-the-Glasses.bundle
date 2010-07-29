import re, urllib
from PMS import *

TGWTG_PREFIX                   = '/video/thatguywiththeglasses'
TGWTG_URL                      = 'http://thatguywiththeglasses.com'
IMAGE_BASEURL                  = "http://a.images.blip.tv/"

DEBUG                         = True
CACHE_FRONTPAGE               = 64000 
CACHE_SHOWPAGE                = CACHE_FRONTPAGE
CACHE_RSS                     = 3200
CACHE_EPISODE_RSS             = 640000 # This contains just one show so we can cache for ages

RSS_NAMESPACE                  = {'media':'http://search.yahoo.com/mrss/', 'blip':'http://blip.tv/dtd/blip/1.0'}

####################################################################################################

def Start():
  Plugin.AddPrefixHandler(TGWTG_PREFIX, ShowSelector, L('tgwtg'), 'icon-default.png', 'art-default.png')
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('Details', viewMode='InfoList', mediaType='items')
  MediaContainer.content = 'Items'
  MediaContainer.art = R('art-default.png')
  MediaContainer.viewGroup = 'List'
  MediaContainer.title1 = L('tgwtg')

def UpdateCache():

  HTTP.Request(TGWTG_URL, cacheTime=CACHE_FRONTPAGE)

def ShowSelector(sender=None, parentID='', title1=L('tgwtg'), title2=''):

  # The parent number is the id of the partent li item, the root item is called item54
  # Update : Removed, parentID is now empty for the root element

  dir = MediaContainer()

  page = XML.ElementFromURL(TGWTG_URL, isHTML=True, cacheTime=CACHE_FRONTPAGE)

  # Unfortunately there is no 'ends-width' function in xpath1, so we have this ugly incantation
  #parent = page.xpath("//li[substring(@class, string-length(@class) - string-length('" + parentID + "') + 1, string-length(@class)) = '" + parentID + "']")[0]
  # Update: Removed, now a different code for the root element
  
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
      dir.Append(Function(DirectoryItem(ShowSelector, title=title, thumb=R('icon-default.png')), parentID=childID, title1=title2, title2=title))
    else:
      # Is not a parent, is a show, so pass to ShowBrowser
      childId = liClass
      dir.Append(Function(DirectoryItem(ShowBrowser, title=title, thumb=R('icon-default.png')), showUrl=url, order=title, title1=title2))

  return dir

def ShowBrowser(sender, showUrl, order, title1):

  dir = MediaContainer()

  dir.title1 = title1
  dir.title2 = L(order)
  dir.viewGroup = 'Details'

  showPage = XML.ElementFromURL(showUrl, isHTML=True, cacheTime=CACHE_SHOWPAGE)

  episodes = showPage.xpath("//tr[starts-with(@class,'sectiontableentry')]")

  for episode in episodes:
    url = TGWTG_URL + episode.xpath("./td[position()=2]/a")[0].get('href')
    title = TidyString(episode.xpath("./td[position()=2]/a")[0].text)
    # The author, date and vides metadata is a bit all over the place so we make the best we can
    field1 = TidyString(episode.xpath("./td[position()=3]")[0].text)
    # Update : field2 is sometimes absent
    try:
      field2 = TidyString(episode.xpath("./td[position()=4]")[0].text)
    except:
      field2 = ''
    try:
      field3 = TidyString(episode.xpath("./td[position()=5]")[0].text)
    except:
      field3 = ''

    subtitle = ''
    if field1 != '':
      subtitle += field1 + "\n"
    if re.match(r'^\d+', field2):
      subtitle += "Views: " + field2 + "\n"
    elif field2 !='':
      subtitle += field2 + "\n"
    if re.match(r'^\d+', field3):
      subtitle += "Views: " + field3 + "\n"
    elif field3 != '':
       subtitle += field3 + "\n"

    # We want to rewrite the request for the thumbnail back into the plugin so it can fetch the feed for the show
    thumbNailUrl = Function(ThumbnailLookup, key=url)

    description = ''

    # If this show has been browsed before and the thumbnail loaded we should also have a description
    if Dict.HasKey('description-'+url):
      description = str(Dict.Get('description-'+url))

    # Add some padding to the description
    for i in range(1, subtitle.count('\n')):
      description = "\n" + description

    # Note: Even if the dictionary now contains a 'thumb-'+url entry we don't return that here as it will miss the existing cache within Plex itself

    dir.Append(Function(VideoItem(BlipRedirect, title=title, subtitle=subtitle, thumb=thumbNailUrl, summary=description), episodeUrl=url, mode='video'))

  return dir

def ThumbnailLookup(key):

  # This function provides a redirect to the thumbnail for the reqeusted show page
  if DEBUG:
    PMS.Log(key)
  return BlipRedirect(None, key, mode='thumb')

def BlipRedirect(sender, episodeUrl, mode='video'):

  # This is a bit tricky, we have to hack about to find the rss feed for the episode, then get the flv or thumbnail from that

  # If we already have a value in the dictionary return that

  if mode=='video':
    if Dict.HasKey('video-'+episodeUrl):
      if DEBUG:
        PMS.Log ("Returning from dictionary %s" % Dict.Get('video-'+episodeUrl))
      return Redirect(Dict.Get('video-'+episodeUrl))
  elif mode=='thumb':
    if Dict.HasKey('thumb-'+episodeUrl):
      if DEBUG:
        PMS.Log ("Returning from dictionary %s" % Dict.Get('thumb-'+episodeUrl))
      return Redirect(Dict.Get('thumb-'+episodeUrl))

  if DEBUG:
    PMS.Log(episodeUrl)
  episodePage = XML.ElementFromURL(episodeUrl, isHTML=True, cacheTime=CACHE_SHOWPAGE)
    
  # Get the blip tv url (like http://blip.tv/play/dkflnbdfkbn)
  blipPlayUrl = episodePage.xpath("//center/embed")[0].get('src')

  # The blipPlayUrl will return a 302 redirect, we want the value of this redirect, rather than the target page contents
  if DEBUG:
    PMS.Log('Fetching URL %s' % blipPlayUrl)
  blipRedirect = urllib.urlopen(blipPlayUrl)
  
  # Finally we can find the rssUrl
  # Update: sometimes the file parameter will be the last one, so no & after it
  rssUrl = re.search( r'file=([^&]+)(&|)', str(blipRedirect.geturl())).group(1)
  # Some urls are a bit busted
  rssUrl = re.sub(r'%3A', r':', rssUrl)
  rssUrl = re.sub(r'%2F', r'/', rssUrl)
  if DEBUG:
    PMS.Log('Got File URL %s' % rssUrl)
     
  # Grab the RSS
  # feedparser is broken for media:thumbnail at the moment
  # It was supposed to be fixed here: http://code.google.com/p/feedparser/issues/detail?id=100
  # But in testing the feedparser.py needs this
  #                   'http://search.yahoo.com/mrss':                         'media',
  # Changing to
  #                   'http://search.yahoo.com/mrss/':                         'media',
  # Then it all works

  # This can be restored when feedparser.py is fixed
  #feed = RSS.FeedFromString(HTTP.Request(rssUrl, cacheTime=CACHE_EPISODE_RSS))
  #entry = feed.entries[0]
  #videoUrl = entry.enclosures[0].url
  #thumbnailUrl = entry.media_thumbnail[0]['url']

  feed = XML.ElementFromURL(rssUrl, isHTML=False, cacheTime=CACHE_EPISODE_RSS)

  videoUrl = feed.xpath("//enclosure")[0].get('url')
  thumbnailUrl = feed.xpath("//media:thumbnail", namespaces=RSS_NAMESPACE)[0].get('url')
  description = feed.xpath("//blip:puredescription", namespaces=RSS_NAMESPACE)[0].text

  # Save these in the dictionary for future use
  Dict.Set('thumb-'+episodeUrl, thumbnailUrl)
  Dict.Set('video-'+episodeUrl, videoUrl)
  Dict.Set('description-'+episodeUrl, description)

  if mode == 'video':
    if DEBUG:
      PMS.Log("Sending video redirect to %s" % videoUrl)
    return Redirect(videoUrl)
  else: 
    if DEBUG:
      PMS.Log("Sending thumbnail redirect to %s" % thumbnailUrl)
    return Redirect(thumbnailUrl)


def TidyString(stringToTidy):
  # Function to tidy up strings, 'strip' seems to have issues in some cases so we use a regex
  if stringToTidy:
    # Strip new lines
    stringToTidy = re.sub(r'\n', r' ', stringToTidy)
    # Strip leading / trailing spaces
    stringSearch = re.search(r'^\s*(\S.*?\S?)\s*$', stringToTidy)
    if stringSearch == None: 
      return ''
    else:
      return stringSearch.group(1)
  else:
    return ''

