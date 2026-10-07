using System.Collections;
using System.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.XR.ARFoundation;
/// Fake async provider exercises adoption/cleanup; never certifies physical ARCore tracking.
public class HonorsAnchorProviderTests {
    class Fake:IHonorsAnchorProvider {public int calls;public TaskCompletionSource<HonorsAnchorResult> pending=new TaskCompletionSource<HonorsAnchorResult>();public Task<HonorsAnchorResult> Add(Pose p){calls++;return pending.Task;}}
    static ARAnchor MakeAnchor(){var go=new GameObject("synthetic_disabled_anchor");go.SetActive(false);return go.AddComponent<ARAnchor>();}
    [UnityTest] public IEnumerator DisabledAndDestroyedDriverRejectLateResults(){
        var go=new GameObject("late disable test");var c=go.AddComponent<HonorsConfiguration>();c.H2ProfilesAndQA=true;var owner=go.AddComponent<ARImageAnchor>();owner.enabled=false;var d=go.AddComponent<HonorsAnchorDriver>();yield return null;
        var p=JsonUtility.FromJson<ARMarkerProfileRegistry.Bundle>(Resources.Load<TextAsset>("Honors/marker_profiles").text).profiles[0];var fake=new Fake();d.Provider=fake;d.Session.Observe("A",true,0,0);var r=d.Session.Begin("A",new Pose(),p,0);var task=d.ProcessRequest(r,Vector2.one*.2f);Assert.IsTrue(d.NativePending);d.Session.Timeout(9,8);d.Session.Observe("C",true,9,0);var overlap=d.Session.Begin("C",new Pose(),p,9);var denied=d.ProcessRequest(overlap,Vector2.one*.2f);Assert.That(fake.calls,Is.EqualTo(1));Assert.IsTrue(denied.IsCompleted);d.enabled=false;var late=MakeAnchor();fake.pending.SetResult(new HonorsAnchorResult(true,late));yield return null;Assert.IsTrue(task.IsCompleted);Assert.IsFalse(d.NativePending);Assert.IsTrue(late==null);Assert.IsFalse(owner.HasAnchor);
        d.enabled=true;fake=new Fake();d.Provider=fake;d.Session.Observe("B",true,1,0);r=d.Session.Begin("B",new Pose(),p,1);task=d.ProcessRequest(r,Vector2.one*.2f);UnityEngine.Object.Destroy(go);yield return null;late=MakeAnchor();fake.pending.SetResult(new HonorsAnchorResult(true,late));yield return null;Assert.IsTrue(task.IsCompleted);Assert.IsTrue(late==null);
    }
    [UnityTest] public IEnumerator LateResultDoesNotAdoptAndAcceptedReplacementHasSingleRoot(){
        var go=new GameObject("Honors test");var c=go.AddComponent<HonorsConfiguration>();c.H2ProfilesAndQA=true;var owner=go.AddComponent<ARImageAnchor>();var d=go.AddComponent<HonorsAnchorDriver>();
        var p=JsonUtility.FromJson<ARMarkerProfileRegistry.Bundle>(Resources.Load<TextAsset>("Honors/marker_profiles").text).profiles[0];
        var fake=new Fake();d.Provider=fake;d.Session.Observe("A",true,0,0);var request=d.Session.Begin("A",new Pose(),p,0);var task=d.ProcessRequest(request,new Vector2(.2f,.2f));d.Session.Suspend();var late=MakeAnchor();fake.pending.SetResult(new HonorsAnchorResult(true,late));yield return null;Assert.IsTrue(task.IsCompleted);Assert.IsFalse(owner.HasAnchor);Assert.IsTrue(late==null);
        d.Session.Resume();fake=new Fake();d.Provider=fake;d.Session.Observe("B",true,1,0);request=d.Session.Begin("B",new Pose(),p,1);task=d.ProcessRequest(request,new Vector2(.2f,.2f));var accepted=MakeAnchor();fake.pending.SetResult(new HonorsAnchorResult(true,accepted));yield return null;Assert.IsTrue(owner.HasAnchor);var root=owner.ContentRoot;Assert.AreSame(accepted.transform,root.parent);
        fake=new Fake();d.Provider=fake;d.Session.ForceReanchor();d.Session.Observe("C",true,2,0);request=d.Session.Begin("C",new Pose(),p,2);task=d.ProcessRequest(request,new Vector2(.2f,.2f));fake.pending.SetResult(new HonorsAnchorResult(false,null));yield return null;Assert.AreSame(root,owner.ContentRoot);Assert.AreSame(accepted,owner.Anchor);
        fake=new Fake();d.Provider=fake;d.Session.Observe("D",true,3,0);request=d.Session.Begin("D",new Pose(),p,3);task=d.ProcessRequest(request,new Vector2(.2f,.2f));var replacement=MakeAnchor();fake.pending.SetResult(new HonorsAnchorResult(true,replacement));yield return null;Assert.AreSame(root,owner.ContentRoot);Assert.AreSame(replacement.transform,root.parent);Assert.IsTrue(accepted==null);
        UnityEngine.Object.Destroy(go);yield return null;Assert.IsTrue(replacement==null);
    }
}
