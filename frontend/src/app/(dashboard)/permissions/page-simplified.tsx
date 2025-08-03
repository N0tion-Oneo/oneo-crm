  const toggleCategoryPermissions = async (category: string, userTypeName: string) => {
    const categoryPermissions = permissionsByCategory[category] || []
    const userType = userTypes.find(ut => ut.name === userTypeName)
    if (!userType) return

    // Check current state - use the same logic as individual toggles
    const allGranted = categoryPermissions.every(permission => 
      permissionMatrix[userTypeName]?.[permission.name] === true
    )
    const newValue = !allGranted // Toggle: All->None, Some->All, None->All
    
    console.log(`🔄 Category toggle: ${category} for ${userTypeName} → ${newValue ? 'Grant All' : 'Revoke All'}`)

    // Process each permission individually using EXACT same logic as togglePermission
    for (const permission of categoryPermissions) {
      const [schemaCategory, action] = permission.name.split(':')
      
      if (!schemaCategory || !action) {
        console.warn(`Invalid permission format: ${permission.name}`)
        continue
      }

      try {
        console.log(`📤 ${newValue ? 'Adding' : 'Removing'} ${permission.name}`)
        
        // Use IDENTICAL API calls as individual toggles
        let response
        if (newValue) {
          response = await api.post(`/auth/user-types/${userType.id}/add_permission/`, {
            category: schemaCategory,
            action
          })
        } else {
          response = await api.post(`/auth/user-types/${userType.id}/remove_permission/`, {
            category: schemaCategory,
            action
          })
        }
        
        // Update state after each API call (like individual toggles)
        if (response.data && response.data.base_permissions) {
          setUserTypes(prev => prev.map(ut => {
            if (ut.id === userType.id) {
              return { ...ut, base_permissions: response.data.base_permissions }
            }
            return ut
          }))
        }
        
        console.log(`✅ ${permission.name} ${newValue ? 'added' : 'removed'}`)
      } catch (error: any) {
        console.error(`Failed to ${newValue ? 'add' : 'remove'} ${permission.name}:`, error?.response?.data)
      }
    }
    
    showNotification(`${newValue ? 'Granted' : 'Revoked'} all ${category} permissions for ${userTypeName}`, 'success')
  }