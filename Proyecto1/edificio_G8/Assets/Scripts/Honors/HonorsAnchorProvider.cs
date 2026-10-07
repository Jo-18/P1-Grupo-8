using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
public readonly struct HonorsAnchorResult {public readonly bool success;public readonly ARAnchor anchor;public HonorsAnchorResult(bool ok,ARAnchor value){success=ok;anchor=value;}}
public interface IHonorsAnchorProvider {Task<HonorsAnchorResult> Add(Pose pose);}
public sealed class HonorsAnchorProvider : IHonorsAnchorProvider {
    readonly ARAnchorManager manager;public HonorsAnchorProvider(ARAnchorManager m){manager=m;}
    public async Task<HonorsAnchorResult> Add(Pose pose){var r=await manager.TryAddAnchorAsync(pose);return new HonorsAnchorResult(r.status.IsSuccess(),r.value);}
}
