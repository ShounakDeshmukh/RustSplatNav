use anyhow::Result;
use builtin_interfaces::msg::Time;
use geometry_msgs::msg::TwistStamped;
use rclrs::{Context, CreateBasicExecutor, RclrsErrorFilter, SpinOptions};
use std::time::Duration;

/// Publishes cmd_vel commands that make the robot rotate in place.
fn main() -> Result<()> {
    let context: Context = Context::default_from_env()?;
    let mut executor = context.create_basic_executor();
    let node = executor.create_node("spin_robot_node")?;

    let publisher = node.create_publisher::<TwistStamped>("/j100/cmd_vel")?;
    let _timer = node
        .clone()
        .create_timer_repeating(Duration::from_millis(100), move || {
            let mut msg = TwistStamped::default();
            let now = node
                .get_clock()
                .now()
                .to_ros_msg()
                .expect("failed to get current time");
            msg.header.stamp = Time {
                sec: now.sec,
                nanosec: now.nanosec,
            };
            msg.twist.linear.x = 0.0;
            msg.twist.angular.z = 0.6;

            if let Err(err) = publisher.publish(&msg) {
                eprintln!("publish failed: {err}");
            }
        })?;

    println!("Publishing spin commands to /j100/cmd_vel");
    executor.spin(SpinOptions::default()).first_error()?;
    Ok(())
}
