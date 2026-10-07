using NUnit.Framework;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

public class ARInputRegressionTests : InputTestFixture
{
    Touchscreen screen;
    public override void Setup(){base.Setup();screen=InputSystem.AddDevice<Touchscreen>();}
    public override void TearDown(){base.TearDown();}
    void Touch(int id, Vector2 position)
    {
        BeginTouch(id,position,screen:screen);
    }
    [Test] public void SingleTouchPressHasPositionAndDoesNotRepeat()
    {
        var expected=new Vector2(100,200);
        Touch(1,expected);
        Assert.IsTrue(ARPointerInput.TryPress(out var position));
        Assert.AreEqual(expected,position);
        InputSystem.Update();
        Assert.IsFalse(ARPointerInput.TryPress(out _));
    }
    [Test] public void MultipleTouchesDoNotPick()
    {
        Touch(1,new Vector2(100,200));
        Touch(2,new Vector2(200,200));
        Assert.IsFalse(ARPointerInput.TryPress(out _));
    }
}
