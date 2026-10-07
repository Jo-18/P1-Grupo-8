from pathlib import Path
p=Path(__file__).resolve().parents[2]/'Proyecto1/edificio_G8/Assets/Scripts/Honors/ARRegistrationRecorder.cs'
s=p.read_text(encoding='utf-8')
s=s.replace('monotonicSeconds,run,marker,profile,','monotonicSeconds,run,marker,trackableId,profile,')
s=s.replace('run,s.marker,s.profile,','run,s.marker,s.trackableId,s.profile,')
p.write_text(s,encoding='utf-8')
p=Path(__file__).resolve().parents[2]/'Proyecto1/edificio_G8/Assets/Scripts/Honors/HonorsAnchorDriver.cs'
s=p.read_text(encoding='utf-8').replace('marker=marker!=null?marker.referenceImage.name:"",profile=', 'marker=marker!=null?marker.referenceImage.name:"",trackableId=marker!=null?marker.trackableId.ToString():"",profile=')
p.write_text(s,encoding='utf-8')
