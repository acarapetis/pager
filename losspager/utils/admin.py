#stdlib imports
import os.path
import datetime
import zipfile
import glob
import re
import shutil
import json

#local imports
from losspager.utils.exception import PagerException
from losspager.utils.config import read_config,write_config
from losspager.io.pagerdata import PagerData

#third-party imports
from impactutils.comcat.query import ComCatInfo
import pandas as pd

DATETIMEFMT = '%Y%m%d%H%M%S'
EIGHT_HOURS = 8 * 3600

class PagerAdmin(object):
    def __init__(self,pager_folder,archive_folder):
        if not os.path.isdir(pager_folder):
            raise PagerException('PAGER data output folder %s does not exist.' % pager_folder)
        self._pager_folder = pager_folder
        if not os.path.isdir(archive_folder):
            os.makedirs(archive_folder)
        self._archive_folder = archive_folder

    def createEventFolder(self,eventid,event_time):
        eventfolder = os.path.join(self._pager_folder,eventid+'_'+event_time.strftime(DATETIMEFMT))
        #look for folder with that event id in the pager_folder
        teventfolder = self.getEventFolder(eventid)
        if teventfolder is not None:
            return teventfolder
        else:
            try:
                ccinfo = ComCatInfo(eventid)
                #try to get all the possible event ids before failing
                authid,allids = ccinfo.getAssociatedIds()
                allids.append(authid)
                for eid in allids:
                    eventfolder = os.path.join(outfolder,eid+event_time.strftime(DATETIMEFMT))
                    if os.path.isdir(eventfolder):
                        return eventfolder
            except:
                pass
        if not os.path.isdir(eventfolder):
            os.makedirs(eventfolder)
        return eventfolder

    def getEventFolder(self,eventid):
        eventfolders = glob.glob(os.path.join(self._pager_folder,'*%s*' % eventid))
        if len(eventfolders):
            return eventfolders[0]
        return None
        
    def archiveEvent(self,eventid):
        eventfolder = self.getEventFolder(eventid)
        fpath,eventname = os.path.split(eventfolder)
        if eventfolder is None:
            return False
        zipname = os.path.join(self._archive_folder,eventname+'.zip')
        myzip = zipfile.ZipFile(zipname,mode='w',compression=zipfile.ZIP_DEFLATED)
        for root,dirs,files in os.walk(eventfolder):
            arcfolder = root[root.find(eventid):]
            for fname in files:
                arcfile = os.path.join(arcfolder,fname)
                fullfile = os.path.join(root,fname)
                myzip.write(fullfile,arcfile)

        myzip.close()
        shutil.rmtree(eventfolder)
        return True

    def getAllEventFolders(self):
        all_events = os.listdir(self._pager_folder)
        event_folders = []
        for event in all_events:
            event_folder = os.path.join(self._pager_folder,event)
            jsonfile = os.path.join(event_folder,'version.001' ,'json','event.json')
            if os.path.isfile(jsonfile):
                event_folders.append(event_folder)
        return event_folders

    def getAllEvents(self):
        all_events = os.listdir(self._pager_folder)
        events = []
        for event in all_events:
            event_folder = os.path.join(self._pager_folder,event)
            if os.path.isdir(event_folder):
                if event.find('_') > -1:
                    eventid,etime = event.split('_')
                else:
                    eventid = event
                events.append(eventid)
        return events
    
    def archive(self,events=[],all_events=False,events_before=None):
        if all_events ==True and events_before is not None:
            raise PagerException('You cannot choose to archive all events and some events based on time.')
        narchived = 0
        nerrors = 0
        if all_events:
            events = self.getAllEvents()
            for eventid in events:
                result = self.archiveEvent(eventid)
                if result:
                    narchived += 1
                else:
                    nerrors += 1
        else:
            for eventid in events:
                eventfolder = self.getEventFolder(eventid)
                if events_before is not None:
                    t,etimestr = eventfolder.split('_')
                    etime = datetime.datetime.strptime(etimestr,DATETIMEFMT)
                    if etime < events_before:
                        result = self.archiveEvent(eventid)
                        if result:
                            narchived += 1
                        else:
                            nerrors += 1
                    else:
                        continue
                else:
                    self.archiveEvent(eventid)
                
        return (narchived,nerrors)

    def restoreEvent(self,archive_file):
        myzip = zipfile.ZipFile(archive_file,'r')
        fpath,fname = os.path.split(archive_file)
        eventf,ext = os.path.splitext(fname)
        event_folder = os.path.join(self._pager_folder,eventf)
        if os.path.isdir(event_folder):
            # fmt = 'Event %s could not be restored because there is an event by the same name in the output!'
            # raise PagerException(fmt % fname)
            return False
        myzip.extractall(path=self._pager_folder)
        myzip.close()
        os.remove(archive_file)
        return True
    
    def restore(self,events=[],all_events=False):
        nrestored = 0
        if all:
            zipfiles = glob.glob(os.path.join(self._archive_folder,'*.zip'))
            for zipfile in zipfiles:
                result = self.restoreEvent(zipfile)
                nrestored += result
        else:
            for event in events:
                archived_events = glob.glob(os.path.join(self._archive_folder,'%s_*.zip' % event))
                if len(archived_events):
                    result = self.restoreEvent(archived_events[0])
                    nrestored += result
        return nrestored

    def stop(self,eventid):
        eventfolder = self.getEventFolder(eventid)
        stopfile = os.path.join(eventfolder,'stop')
        if os.path.isfile(stopfile):
            return (False,eventfolder)
        else:
            f = open(stopfile,'wt')
            f.write('Stopped: %s UTC' % datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
            f.close()
        return (True,eventfolder)

    def unstop(self,eventid):
        eventfolder = self.getEventFolder(eventid)
        stopfile = os.path.join(eventfolder,'stop')
        if not os.path.isfile(stopfile):
            return (False,eventfolder)
        else:
            os.remove(stopfile)
        return (True,eventfolder)

    def isStopped(self,eventid):
        eventfolder = self.getEventFolder(eventid)
        stopfile = os.path.join(eventfolder,'stop')
        if not os.path.isfile(stopfile):
            return False
        return True

    def setStatus(self,status='secondary'):
        config = read_config()
        config_file = get_config_file()
        if 'status' not in config:
            lines = open(config_file,'rt').readlines()
            lines.append('status : %s\n' % status)
        else:
            f = open(config_file,'wt')
            for line in lines:
                parts = line.split(':')
                if parts[0].strip() == 'status':
                    line = 'status : %s\n' % status
                else:
                    pass
                f.write(line)
            f.close()
        return True

    def getStatus(self):
        config = read_config()
        status = 'secondary'
        if 'status' in config and config['status'] == 'primary':
            return 'primary'
        return status

    def getVersionNumbers(self,event_folder):
        version_folders = glob.glob(os.path.join(event_folder,'version.*'))
        vnums = []
        for vfolder in version_folders:
            fpath,vf = os.path.split(vfolder)
            vnum = int(re.search('\d+',vf).group())
            vnums.append(vnum)

        vnums.sort()
        return vnums

    def toggleTsunami(self,eventid,tsunami='off'):
        toggle = {'on':1,'off':0}
        event_folder = self.getEventFolder(eventid)
        tsunami_file = os.path.join(event_folder,'tsunami')
        f = open(tsunami_file,'wt')
        f.write('%s' % tsunami)
        f.close()
        
        version_folders = sorted(glob.glob(os.path.join(event_folder,'version.*')))
        jsonfile = os.path.join(version_folders[-1],'json','event.json')
        f = open(jsonfile,'rt')
        jdict = json.load(f)
        f.close()
        if jdict['event']['tsunami'] == tsunami:
            return False
        jdict['event']['tsunami'] = toggle[tsunami]
        f = open(jsonfile,'wt')
        json.dump(jdict,f)
        f.close()
        return True
        
    
    def query(self,start_time=datetime.datetime(1800,1,1),end_time=datetime.datetime.utcnow(),
              mag_threshold=0.0,alert_threshold='green',version='last',eventid=None):
        levels = {'green':0,
                  'yellow':1,
                  'orange':2,
                  'red':3}
        if eventid is not None:
            all_event_folders = [self.getEventFolder(eventid)]
            version = 'all'
        else:
            all_event_folders = self.getAllEventFolders()
        event_data = []
        df = pd.DataFrame(columns=PagerData.getSeriesColumns())
        jsonfolders = []
        for event_folder in all_event_folders:
            vnums = self.getVersionNumbers(event_folder)
            if version == 'first':
                vnum = vnums[0]
                jsonfolders.append(os.path.join(event_folder,'version.%03d' % vnum,'json'))
            elif version == 'last':
                vnum = vnums[-1]
                jsonfolders.append(os.path.join(event_folder,'version.%03d' % vnum,'json'))
            elif version == 'eight':
                for vnum in vnums:
                    jsonfolder = os.path.join(event_folder,'version.%03d' % vnum,'json')
                    pdata = PagerData()
                    pdata.loadFromJSON(jsonfolder)
                    if pdata.processing_time >= pdata.time + datetime.timedelta(seconds=EIGHT_HOURS):
                        break
                    jsonfolders.append(jsonfolder)
            elif version == 'all':
                for vnum in vnums:
                    jsonfolder = os.path.join(event_folder,'version.%03d' % vnum,'json')
                    jsonfolders.append(jsonfolder)
            else:
                raise PagerException('version option "%s" not supported.' % version)

        for jsonfolder in jsonfolders:
            pdata = PagerData()
            pdata.loadFromJSON(jsonfolder)
            meetsLevel = levels[pdata.summary_alert] >= levels[alert_threshold]
            meetsMag = pdata.magnitude >= mag_threshold
            if pdata.time >= start_time and pdata.time <= end_time and meetsLevel and meetsMag:
                row = pdata.toSeries()
                df = df.append(row,ignore_index=True)
        df.Version = df.Version.astype(int)
        df = df.sort_values('EventTime')
        df = df.set_index('EventID')
        return df
        
    
