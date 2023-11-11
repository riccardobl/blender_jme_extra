from .Exporter import Exporter
class RigidBodyExporter(Exporter):
   

    def exportFromNode( self,gltf2_node, ob, export_settings):
        rigidBody=getattr(ob, 'rigid_body', None)
        if not rigidBody:
            return
        
        rbtype = ob.rigid_body.type
        dynamic = ob.rigid_body.enabled
        mass = ob.rigid_body.mass
        isKinematic = ob.rigid_body.kinematic
        friction = ob.rigid_body.friction
        restitution = ob.rigid_body.restitution
        margin = ob.rigid_body.collision_margin

        
        linearDamping = ob.rigid_body.linear_damping
        angularDamping = ob.rigid_body.angular_damping

        angularFactor = [1, 1, 1]
        linearFactor = [1, 1, 1]

        shape = ob.rigid_body.collision_shape

        collision_groups = ob.rigid_body.collision_collections
        collision_group = 0
        i = 0
        for g in collision_groups:
            if g:
                collision_group |= (g<<i)
            i += 1


        collisionMask = collision_group

        ext= {
            'type': rbtype,
            'dynamic': dynamic,
            'mass': mass,
            'isKinematic': isKinematic,
            'friction': friction,
            'restitution': restitution,
            'margin': margin,
            'linearDamping': linearDamping,
            'angularDamping': angularDamping,
            'angularFactor': angularFactor,
            'linearFactor': linearFactor,
            'shape': shape,
            'collisionMask': collisionMask
        }

        gltf2_node.extensions['JME_rigidbody'] = ext


        
