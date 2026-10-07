using System;
using System.IO;
using NUnit.Framework;
using UnityEngine;
public class HonorsRecorderTests {
    [Serializable] class Summary {public ARRegistrationRecorder.Metrics positionMm,angleDeg;public ARRegistrationRecorder.Sample[] samples;}
    [Test] public void RecorderRoundTripSeparatesEventsUnavailableAndPhysicalReferences(){
        var output=Path.Combine(HonorsPaths.Evidence,"QA_test",Guid.NewGuid().ToString("N"));
        using(var recorder=new ARRegistrationRecorder(output)){
            var profiles=JsonUtility.FromJson<ARMarkerProfileRegistry.Bundle>(Resources.Load<TextAsset>("Honors/marker_profiles").text).profiles;recorder.Profiles(profiles);
            var session=new ARAnchorSessionState();session.Observe("A",true,0,0);var request=session.Begin("A",new Pose(Vector3.one,Quaternion.identity),profiles[0],0);recorder.Request(request);
            recorder.Record(new ARRegistrationRecorder.Sample{timestamp=0,eventName="sample",relativeAvailable=true,relativeMm=10,relativeAngleDeg=2,trackableId="test_only"});
            recorder.Record(new ARRegistrationRecorder.Sample{timestamp=.1,eventName="sample",relativeAvailable=false,relativeMm=0,relativeAngleDeg=0});
            recorder.Record(new ARRegistrationRecorder.Sample{timestamp=.2,eventName="state_event",relativeAvailable=true,relativeMm=999,relativeAngleDeg=999});
        }
        var d=Directory.GetDirectories(output)[0];var summary=JsonUtility.FromJson<Summary>(File.ReadAllText(Path.Combine(d,"summary.json")));
        Assert.That(summary.samples.Length,Is.EqualTo(3));Assert.That(summary.positionMm.count,Is.EqualTo(1));Assert.That(summary.positionMm.rms,Is.EqualTo(10));Assert.That(summary.angleDeg.max,Is.EqualTo(2));
        var lines=File.ReadAllLines(Path.Combine(d,"raw.csv"));Assert.That(lines.Length,Is.EqualTo(4));Assert.That(lines[0].Split(',').Length,Is.EqualTo(lines[1].Split(',').Length));
        Assert.That(File.ReadAllLines(Path.Combine(d,"physical_reference_PENDING.csv")).Length,Is.EqualTo(1));Assert.IsTrue(File.Exists(Path.Combine(d,"request_1.json")));Assert.IsTrue(File.Exists(Path.Combine(d,"profiles_snapshot.json")));
    }
}
