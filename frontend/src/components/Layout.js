import React, { useState, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { 
  AppBar, 
  Box, 
  Toolbar, 
  IconButton, 
  Typography, 
  Menu, 
  Container, 
  Avatar, 
  Button, 
  Tooltip, 
  MenuItem, 
  Drawer, 
  List, 
  ListItem, 
  ListItemIcon, 
  ListItemText, 
  Divider 
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import HomeIcon from '@mui/icons-material/Home';
import StoreIcon from '@mui/icons-material/Store';
import HelpIcon from '@mui/icons-material/Help';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import LogoutIcon from '@mui/icons-material/Logout';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import axios from 'axios';

// Import components
import ScrollingAnnouncement from './ScrollingAnnouncement';

// Import CSS styles
import '../styles/components/Layout.css';

const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorElUser, setAnchorElUser] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(false);

  // Check if user is logged in
  const isLoggedIn = localStorage.getItem('token') !== null;
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  
  // Get current page from URL path
  const getCurrentPage = () => {
    const path = location.pathname;
    if (path.includes('marketplace')) return 'marketplace';
    if (path.includes('lost-found')) return 'lost_found';
    if (path.includes('ride')) return 'ride_share';
    return 'home';
  };
  
  // Fetch announcements based on current page
  useEffect(() => {
    const fetchAnnouncements = async () => {
      try {
        setLoading(true);
        const currentPage = getCurrentPage();
        
        // Use the notification service instead of direct axios call
        // to leverage the improved caching and error handling
        const data = await axios.get(`/api/announcements/page/${currentPage}`, {
          headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });
        
        // Only set announcements if we have valid data
        if (Array.isArray(data.data)) {
          setAnnouncements(data.data);
        } else {
          setAnnouncements([]);
        }
      } catch (error) {
        console.error('Error fetching announcements:', error);
        setAnnouncements([]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchAnnouncements();
    
    // Set up a polling interval to refresh announcements periodically
    const intervalId = setInterval(fetchAnnouncements, 30000); // Refresh every 30 seconds
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, [location.pathname]); // Re-fetch when route changes

  const handleOpenUserMenu = (event) => {
    setAnchorElUser(event.currentTarget);
  };

  const handleCloseUserMenu = () => {
    setAnchorElUser(null);
  };

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/');
  };

  const drawer = (
    <Box sx={{ width: 250 }} role="presentation" onClick={handleDrawerToggle}>
      <List>
        <ListItem component={Link} to="/marketplace" sx={{ color: 'inherit', textDecoration: 'none' }}>
          <ListItemIcon>
            <StoreIcon />
          </ListItemIcon>
          <ListItemText primary="Marketplace" />
        </ListItem>
        <ListItem component={Link} to="/lost-found" sx={{ color: 'inherit', textDecoration: 'none' }}>
          <ListItemIcon>
            <HelpIcon />
          </ListItemIcon>
          <ListItemText primary="Lost & Found" />
        </ListItem>
        <ListItem component={Link} to="/ride-booking" sx={{ color: 'inherit', textDecoration: 'none' }}>
          <ListItemIcon>
            <DirectionsCarIcon />
          </ListItemIcon>
          <ListItemText primary="Ride Booking" />
        </ListItem>
      </List>
      <Divider />
    </Box>
  );

  return (
    <>
      <AppBar 
        position="static" 
        sx={{ 
          background: 'linear-gradient(135deg, #1976d2, #115293)',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
        }}
      >
        <Container maxWidth="xl">
          <Toolbar disableGutters>
            <IconButton
              size="large"
              edge="start"
              color="inherit"
              aria-label="menu"
              sx={{ mr: 2 }}
              onClick={handleDrawerToggle}
            >
              <MenuIcon />
            </IconButton>
            <Typography
              variant="h6"
              noWrap
              component={Link}
              to="/"
              sx={{
                mr: 2,
                display: { xs: 'none', md: 'flex' },
                fontFamily: 'monospace',
                fontWeight: 700,
                letterSpacing: '.3rem',
                color: 'inherit',
                textDecoration: 'none',
              }}
            >
              BRACU EUREKA
            </Typography>

            <Box sx={{ flexGrow: 1, display: { xs: 'none', md: 'flex' } }}>
              <Button
                component={Link}
                to="/marketplace"
                sx={{ 
                  my: 2, 
                  color: 'white', 
                  display: 'block',
                  position: 'relative',
                  '&::after': {
                    content: '""',
                    position: 'absolute',
                    bottom: '5px',
                    left: '50%',
                    width: '0',
                    height: '2px',
                    bgcolor: 'white',
                    transition: 'width 0.3s ease, left 0.3s ease'
                  },
                  '&:hover::after': {
                    width: '80%',
                    left: '10%'
                  }
                }}
              >
                Marketplace
              </Button>
              <Button
                component={Link}
                to="/lost-found"
                sx={{ 
                  my: 2, 
                  color: 'white', 
                  display: 'block',
                  position: 'relative',
                  '&::after': {
                    content: '""',
                    position: 'absolute',
                    bottom: '5px',
                    left: '50%',
                    width: '0',
                    height: '2px',
                    bgcolor: 'white',
                    transition: 'width 0.3s ease, left 0.3s ease'
                  },
                  '&:hover::after': {
                    width: '80%',
                    left: '10%'
                  }
                }}
              >
                Lost & Found
              </Button>
              <Button
                component={Link}
                to="/ride-booking"
                sx={{ 
                  my: 2, 
                  color: 'white', 
                  display: 'block',
                  position: 'relative',
                  '&::after': {
                    content: '""',
                    position: 'absolute',
                    bottom: '5px',
                    left: '50%',
                    width: '0',
                    height: '2px',
                    bgcolor: 'white',
                    transition: 'width 0.3s ease, left 0.3s ease'
                  },
                  '&:hover::after': {
                    width: '80%',
                    left: '10%'
                  }
                }}
              >
                Ride Booking
              </Button>
            </Box>

            <Box sx={{ flexGrow: 0 }}>
              {isLoggedIn ? (
                <>
                  <Tooltip title="Open settings">
                    <IconButton 
                      onClick={handleOpenUserMenu} 
                      sx={{ 
                        p: 0,
                        border: '2px solid rgba(255, 255, 255, 0.5)',
                        transition: 'transform 0.2s',
                        '&:hover': {
                          transform: 'scale(1.1)'
                        }
                      }}
                    >
                      <Avatar 
                        alt={user.name || 'User'}
                        sx={{
                          bgcolor: 'secondary.main'
                        }}
                      >
                        {user.name ? user.name.charAt(0).toUpperCase() : <AccountCircleIcon />}
                      </Avatar>
                    </IconButton>
                  </Tooltip>
                  <Menu
                    sx={{ mt: '45px' }}
                    id="menu-appbar"
                    anchorEl={anchorElUser}
                    anchorOrigin={{
                      vertical: 'top',
                      horizontal: 'right',
                    }}
                    keepMounted
                    transformOrigin={{
                      vertical: 'top',
                      horizontal: 'right',
                    }}
                    open={Boolean(anchorElUser)}
                    onClose={handleCloseUserMenu}
                  >
                    <MenuItem onClick={handleCloseUserMenu}>
                      <Typography textAlign="center">Profile</Typography>
                    </MenuItem>
                    <MenuItem onClick={handleLogout}>
                      <Typography textAlign="center">Logout</Typography>
                    </MenuItem>
                  </Menu>
                </>
              ) : (
                <Button
                  component={Link}
                  to="/login"
                  color="inherit"
                  sx={{
                    border: '1px solid rgba(255, 255, 255, 0.5)',
                    borderRadius: '20px',
                    px: 3,
                    '&:hover': {
                      bgcolor: 'rgba(255, 255, 255, 0.1)'
                    }
                  }}
                >
                  Login
                </Button>
              )}
            </Box>
          </Toolbar>
        </Container>
      </AppBar>
      
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={handleDrawerToggle}
        PaperProps={{
          sx: {
            width: 250,
            background: 'linear-gradient(135deg, #f5f7fa, #e4edf9)',
            boxShadow: '0 0 20px rgba(0, 0, 0, 0.1)'
          }
        }}
      >
        {drawer}
      </Drawer>
      
      {/* Display announcements for the current page */}
      {announcements && announcements.length > 0 && (
        <Box sx={{ width: '100%', mt: 2 }}>
          <Container maxWidth="lg">
            <ScrollingAnnouncement 
              announcements={announcements} 
              page={getCurrentPage()} 
            />
          </Container>
        </Box>
      )}
      
      <Container 
        maxWidth="lg" 
        sx={{ 
          mt: 4, 
          mb: 4,
          position: 'relative',
          zIndex: 1
        }}
      >
        <Outlet />
      </Container>
    </>
  );
};

export default Layout; 