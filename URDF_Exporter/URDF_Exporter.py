#Author-syuntoku14
#Author-spacemaster85
#Modified on Sun Jan 17 2021
#Description-Generate URDF file from Fusion 360

import adsk, adsk.core, adsk.fusion, traceback
import os
import datetime

"""
# length unit is 'cm' and inertial unit is 'kg/cm^2'
# If there is no 'body' in the root component, maybe the corrdinates are wrong.
"""

# joint effort: 100
# joint velocity: 100
# supports "Revolute", "Rigid" and "Slider" joint types



# I'm not sure how prismatic joint acts if there is no limit in fusion model

def _debug(msg):
    print('Fusion2URDF: {}'.format(msg))
    try:
        log_path = os.path.join(os.path.dirname(__file__), 'fusion2urdf_debug.log')
        with open(log_path, 'a') as log_file:
            log_file.write('{} {}\n'.format(
                datetime.datetime.now().isoformat(timespec='seconds'), msg))
    except Exception:
        pass


def run(context):
    ui = None
    success_msg = 'Successfully create URDF file'
    msg = success_msg

    try:
        # --------------------
        # initialize
        app = adsk.core.Application.get()
        ui = app.userInterface
        _debug('run() started')
        from .utils import utils
        from .core import Link, Joint, Write
        _debug('imports succeeded')
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        title = 'Fusion2URDF'
        if not design:
            _debug('no active Fusion design')
            ui.messageBox('No active Fusion design', title)
            return

        root = design.rootComponent  # root component 
        components = design.allComponents

        # set the names        
        robot_name = root.name.split()[0].lower()
        package_name = robot_name + '_description'
        _debug('root={} robot_name={} opening folder dialog'.format(root.name, robot_name))
        save_dir = utils.file_dialog(ui)
        if save_dir == False:
            _debug('folder dialog canceled')
            ui.messageBox('Fusion2URDF was canceled', title)
            return 0
        _debug('save_dir={}'.format(save_dir))

        ros_result = ui.messageBox(
            'Choose ROS version.\n\nYes = ROS 2\nNo = ROS 1',
            title,
            adsk.core.MessageBoxButtonTypes.YesNoCancelButtonType)
        if ros_result == adsk.core.DialogResults.DialogCancel:
            _debug('ROS version dialog canceled')
            ui.messageBox('Fusion2URDF was canceled', title)
            return 0
        use_ros2 = (ros_result == adsk.core.DialogResults.DialogYes)
        _debug('use_ros2={}'.format(use_ros2))

        save_dir= save_dir + '/' + package_name
        try: os.mkdir(save_dir)
        except: pass  


        package_dir_ros1 = os.path.abspath(os.path.dirname(__file__)) + '/package_ros1/'
        package_dir_ros2 = os.path.abspath(os.path.dirname(__file__)) + '/package_ros2/'        
        # --------------------
        # set dictionaries
        
        # Generate joints_dict. All joints are related to root. 
        joints_dict, msg = Joint.make_joints_dict(root, msg)
        if msg != success_msg:
            _debug('make_joints_dict failed: {}'.format(msg))
            ui.messageBox(msg, title)
            return 0   
        print(joints_dict)
        # Generate inertial_dict
        inertial_dict, msg = Link.make_inertial_dict(root, msg)
        if msg != success_msg:
            _debug('make_inertial_dict failed: {}'.format(msg))
            ui.messageBox(msg, title)
            return 0
        elif not 'base_link' in inertial_dict:
            msg = 'There is no base_link. Please set base_link and run again.'
            _debug(msg)
            ui.messageBox(msg, title)
            return 0
        
        material_dict, color_dict, msg = Link.make_material_dict(root, msg)
        if msg != success_msg:
            _debug('make_material_dict failed: {}'.format(msg))
            ui.messageBox(msg, title)
            return 0  
        
        links_xyz_dict = {} 
        # --------------------
        # Generate URDF
        Write.write_urdf(joints_dict, links_xyz_dict, inertial_dict, material_dict, package_name, robot_name, save_dir, not use_ros2)
        Write.write_materials_xacro(color_dict, robot_name, save_dir)
        Write.write_transmissions_xacro(joints_dict, links_xyz_dict, robot_name, save_dir)
        if use_ros2:

            utils.copy_package(save_dir, package_dir_ros2)
            utils.update_cmakelists(save_dir, package_name)
            utils.update_package_xml(save_dir, package_name)
            utils.update_ros2_launchfile(save_dir, robot_name)
        else:
            Write.write_gazebo_xacro(joints_dict, links_xyz_dict, inertial_dict, package_name, robot_name, save_dir)
            Write.write_display_launch(package_name, robot_name, save_dir)
            Write.write_gazebo_launch(package_name, robot_name, save_dir)
            Write.write_control_launch(package_name, robot_name, save_dir, joints_dict)
            Write.write_yaml(package_name, robot_name, save_dir, joints_dict)
 
            utils.copy_package(save_dir, package_dir_ros1)
            utils.update_cmakelists(save_dir, package_name)
            utils.update_package_xml(save_dir, package_name)

        # Generate STl files        
        _debug('exporting STL files to {}'.format(save_dir))
        utils.export_stl(app, save_dir)   

        _debug('finished: {}'.format(msg))
        ui.messageBox(msg, title)
        
    except:
        err = traceback.format_exc()
        _debug('FAILED\n{}'.format(err))
        if ui:
            ui.messageBox('Failed:\n{}'.format(err))
